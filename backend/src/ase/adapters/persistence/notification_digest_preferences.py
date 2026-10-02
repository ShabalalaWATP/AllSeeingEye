"""Preference changes and digest progress are serialised by the account guard."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.notification_digest_models import (
    DigestDeliveryRow,
    DigestPreferenceRow,
)
from ase.domain.notification_digest import DigestPreferences, next_digest_at


class SqlDigestPreferences:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> DigestPreferences:
        row = await self._session.get(DigestPreferenceRow, user_id, populate_existing=True)
        return (
            DigestPreferences(row.enabled, row.timezone, row.hour) if row else DigestPreferences()
        )

    async def save(self, user_id: UUID, preferences: DigestPreferences, now: datetime) -> None:
        if not preferences.enabled:
            await cancel_pending_digests(self._session, user_id)
        row = await self._session.get(DigestPreferenceRow, user_id, populate_existing=True)
        start = row.cursor_at if row is not None and row.enabled and preferences.enabled else now
        await self._session.merge(
            DigestPreferenceRow(
                user_id=user_id,
                enabled=preferences.enabled,
                timezone=preferences.timezone,
                hour=preferences.hour,
                cursor_at=start,
                next_due_at=next_digest_at(now, preferences),
            )
        )


async def cancel_pending_digests(session: AsyncSession, user_id: UUID) -> None:
    # A send already in progress may have been accepted externally. Fence its
    # outcome conservatively, and never revive old windows when opting in again.
    await session.execute(
        update(DigestDeliveryRow)
        .where(
            DigestDeliveryRow.user_id == user_id,
            DigestDeliveryRow.state.in_(("pending", "unavailable", "sending")),
        )
        .values(
            state=case((DigestDeliveryRow.state == "sending", "uncertain"), else_="cancelled"),
            safe_reason="opted_out",
        )
    )
