"""Bounded multi-worker digest admission stores each window and cursor transactionally."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.models import UserRow
from ase.adapters.persistence.notification_digest_models import (
    DigestDeliveryRow,
    DigestPreferenceRow,
)
from ase.application.access import AccessPolicy
from ase.domain.errors import Forbidden, NotFound, Unauthenticated
from ase.domain.notification_digest import DigestPreferences, latest_digest_slot, next_digest_at

NAMESPACE = UUID("15a5cac5-ff58-44c5-9a20-5e2c3636845b")


class SqlDigestScheduler:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        access: Callable[[AsyncSession], AccessPolicy],
    ) -> None:
        self._sessions, self._access = sessions, access

    async def enqueue_due(self, now: datetime) -> int:
        async with self._sessions() as session:
            ids = list(
                await session.scalars(
                    select(DigestPreferenceRow.user_id)
                    .join(
                        UserRow,
                        UserRow.id == DigestPreferenceRow.user_id,
                    )
                    .where(
                        UserRow.is_active.is_(True),
                        DigestPreferenceRow.enabled.is_(True),
                        DigestPreferenceRow.next_due_at <= now,
                    )
                    .order_by(DigestPreferenceRow.next_due_at, DigestPreferenceRow.user_id)
                    .limit(100)
                )
            )
        admitted = 0
        for user_id in ids:
            async with self._sessions() as session:
                try:
                    await self._access(session).background(user_id, None, for_update=True)
                except (Forbidden, NotFound, Unauthenticated):
                    continue
                row = await session.get(DigestPreferenceRow, user_id, populate_existing=True)
                if row is None or not row.enabled or row.next_due_at > now:
                    continue
                preferences = DigestPreferences(row.enabled, row.timezone, row.hour)
                slot = latest_digest_slot(now, preferences)
                key = uuid5(NAMESPACE, f"{user_id}:{slot.local.date().isoformat()}")
                existing = await session.get(DigestDeliveryRow, key)
                if existing is None and row.cursor_at < slot.utc:
                    insert = (
                        sqlite_insert if session.get_bind().dialect.name == "sqlite" else pg_insert
                    )
                    await session.execute(
                        insert(DigestDeliveryRow)
                        .values(
                            id=key,
                            user_id=user_id,
                            local_day=slot.local.date().isoformat(),
                            timezone=row.timezone,
                            window_start=row.cursor_at,
                            window_end=slot.utc,
                            state="pending",
                            attempts=0,
                            created_at=now,
                            updated_at=now,
                        )
                        .on_conflict_do_nothing()
                    )
                    row.cursor_at = slot.utc
                    admitted += 1
                row.next_due_at = next_digest_at(now, preferences)
                await session.commit()
        return admitted
