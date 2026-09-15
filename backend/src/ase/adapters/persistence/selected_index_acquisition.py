"""Short, reauthorised database transactions for selected-index acquisition."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.schedules import _from_row
from ase.adapters.persistence.selected_index_gaps import SqlSelectedIndexGapRepository
from ase.adapters.persistence.selected_subscription_index import (
    SqlSelectedSubscriptionIndexRepository,
)
from ase.application.access import AccessPolicy
from ase.application.schedules.selected_index_types import (
    IndexCursor,
    IndexedPage,
    IndexedSourcePolicy,
)
from ase.domain.errors import Forbidden, NotFound, Unauthenticated
from ase.domain.schedules import Schedule

AccessPolicyFactory = Callable[[AsyncSession], AccessPolicy]


def _same_index_scope(previous: Schedule, current: Schedule) -> bool:
    return (
        previous.id == current.id
        and previous.created_by == current.created_by
        and previous.team_id == current.team_id
        and previous.enabled == current.enabled
        and previous.brief_id == current.brief_id
        and previous.brief_revision == current.brief_revision
        and previous.research_area == current.research_area
        and previous.research_source_ids == current.research_source_ids
        and previous.country_isos == current.country_isos
        and previous.country_iso == current.country_iso
    )


class SqlSelectedIndexAcquisitionStore:
    """No session is held while cache pages are read or a provider performs work."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        access_policy: AccessPolicyFactory,
    ) -> None:
        self.session_factory, self.access_policy = session_factory, access_policy

    async def active_batch(self, after: UUID | None, limit: int) -> tuple[Schedule, ...]:
        if type(limit) is not int or not 1 <= limit <= 32:
            raise ValueError("Selected-index active batch must be bounded")
        async with self.session_factory() as session:
            query = select(ScheduleRow).where(ScheduleRow.enabled.is_(True))
            if after is not None:
                query = query.where(ScheduleRow.id > after)
            rows = await session.scalars(query.order_by(ScheduleRow.id).limit(limit))
            return tuple(_from_row(row) for row in rows)

    async def current(self, subscription_id: UUID) -> Schedule | None:
        async with self.session_factory() as session:
            row = await session.get(ScheduleRow, subscription_id)
            if row is None or not row.enabled:
                return None
            try:
                await self.access_policy(session).background(row.created_by, row.team_id)
            except (Forbidden, NotFound, Unauthenticated):
                return None
            return _from_row(row)

    async def cursor(self, schedule: Schedule, source_id: str) -> IndexCursor | None:
        async with self.session_factory() as session:
            row = await session.get(ScheduleRow, schedule.id)
            if (
                row is None
                or not row.enabled
                or (row.created_by, row.team_id) != (schedule.created_by, schedule.team_id)
            ):
                return None
            access = await self.access_policy(session).background(row.created_by, row.team_id)
            cursor = await SqlSelectedSubscriptionIndexRepository(session).get_cursor(
                schedule.id,
                source_id,
                actor_id=access.actor.id,
                authorised_team_ids=tuple(access.memberships),
            )
            return (
                IndexCursor(
                    cursor.revision, cursor.cursor_value, cursor.watermark_at, cursor.updated_at
                )
                if cursor is not None
                else None
            )

    async def persist(
        self,
        schedule: Schedule,
        policy: IndexedSourcePolicy,
        *,
        expected_revision: int,
        page_key: str,
        page: IndexedPage,
        cursor_value: str | None,
        watermark_at: datetime,
        now: datetime,
    ) -> bool:
        async with self.session_factory() as session:
            try:
                row = await session.get(ScheduleRow, schedule.id)
                if row is None or not row.enabled:
                    return False
                access = await self.access_policy(session).background(
                    row.created_by, row.team_id, for_update=True
                )
                if not _same_index_scope(schedule, _from_row(row)):
                    return False
                await SqlSelectedSubscriptionIndexRepository(session).persist_page(
                    schedule.id,
                    policy.source_id,
                    actor_id=access.actor.id,
                    authorised_team_ids=tuple(access.memberships),
                    expected_revision=expected_revision,
                    page_key=page_key,
                    records=page.records,
                    cursor_value=cursor_value,
                    watermark_at=watermark_at,
                    now=now,
                )
                await session.commit()
                return True
            except BaseException:
                await session.rollback()
                raise

    async def record_gap(
        self,
        schedule: Schedule,
        source_id: str,
        *,
        reason: str,
        start: datetime,
        end: datetime,
        now: datetime,
    ) -> None:
        async with self.session_factory() as session:
            try:
                row = await session.get(ScheduleRow, schedule.id)
                if row is None or not row.enabled:
                    return
                access = await self.access_policy(session).background(
                    row.created_by, row.team_id, for_update=True
                )
                if not _same_index_scope(schedule, _from_row(row)):
                    return
                await SqlSelectedIndexGapRepository(session).record_gap(
                    schedule.id,
                    source_id,
                    actor_id=access.actor.id,
                    authorised_team_ids=tuple(access.memberships),
                    reason=reason,
                    start=start,
                    end=end,
                    now=now,
                )
                await session.commit()
            except BaseException:
                await session.rollback()
                raise
