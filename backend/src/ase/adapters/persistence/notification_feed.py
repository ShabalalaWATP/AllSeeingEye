"""Bounded SQL projections apply notification scope before sorting and limiting."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.notification_models import PrivateFeedTokenRow
from ase.adapters.persistence.operational_models import AlertRow, ScheduleRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionEditionRow
from ase.domain.access import Visibility
from ase.domain.notification_feed import FeedEntry, FeedToken


def _token(row: PrivateFeedTokenRow | None) -> FeedToken | None:
    if row is None:
        return None
    return FeedToken(
        row.user_id, row.token_hash, row.security_version, row.created_at, row.include_titles
    )


class SqlPrivateFeedRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> FeedToken | None:
        return _token(await self._session.get(PrivateFeedTokenRow, user_id, populate_existing=True))

    async def find(self, token_hash: str) -> FeedToken | None:
        return _token(
            await self._session.scalar(
                select(PrivateFeedTokenRow)
                .where(PrivateFeedTokenRow.token_hash == token_hash)
                .execution_options(populate_existing=True)
            )
        )

    async def save(self, token: FeedToken) -> None:
        await self._session.merge(
            PrivateFeedTokenRow(
                user_id=token.user_id,
                token_hash=token.token_hash,
                security_version=token.security_version,
                created_at=token.created_at,
                include_titles=token.include_titles,
            )
        )
        await self._session.flush()

    async def revoke(self, user_id: UUID) -> None:
        await self._session.execute(
            delete(PrivateFeedTokenRow).where(PrivateFeedTokenRow.user_id == user_id)
        )

    async def entries(self, visibility: Visibility, *, limit: int) -> list[FeedEntry]:
        alerts = await self._session.scalars(
            select(AlertRow)
            .where(visibility_predicate(AlertRow.created_by, AlertRow.team_id, visibility))
            .order_by(AlertRow.fired_at.desc(), AlertRow.id.desc())
            .limit(limit)
        )
        rows = [
            FeedEntry(row.id, "alert", row.title, f"/warning?alert={row.id}", row.fired_at)
            for row in alerts
        ]
        editions = await self._session.execute(
            select(SubscriptionEditionRow, ScheduleRow.name)
            .join(ScheduleRow, ScheduleRow.id == SubscriptionEditionRow.subscription_id)
            .where(
                visibility_predicate(ScheduleRow.created_by, ScheduleRow.team_id, visibility),
                ScheduleRow.archived_at.is_(None),
                SubscriptionEditionRow.workflow == "completed",
            )
            .order_by(SubscriptionEditionRow.updated_at.desc(), SubscriptionEditionRow.id.desc())
            .limit(limit)
        )
        rows.extend(
            FeedEntry(
                row.id,
                "edition",
                name,
                f"/subscriptions?subscription={row.subscription_id}&edition={row.id}",
                row.updated_at,
            )
            for row, name in editions
        )
        return sorted(rows, key=lambda row: (row.updated_at, str(row.id)), reverse=True)[:limit]
