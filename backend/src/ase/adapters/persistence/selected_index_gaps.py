"""Short, owner-authorised coverage gap writes for selected subscriptions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.selected_index_eviction import record_index_gap
from ase.adapters.persistence.selected_index_models import SelectedIndexGateRow
from ase.adapters.persistence.selected_subscription_index import (
    SqlSelectedSubscriptionIndexRepository,
)
from ase.domain.errors import Conflict
from ase.domain.selected_subscription_index import _key, _utc


class SqlSelectedIndexGapRepository:
    """The caller owns the transaction; no external request belongs inside it."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_gap(
        self,
        subscription_id: UUID,
        source_id: str,
        *,
        actor_id: UUID,
        authorised_team_ids: tuple[UUID, ...] = (),
        reason: str,
        start: datetime,
        end: datetime,
        now: datetime,
    ) -> None:
        _key(source_id, "source_id", 100)
        checked_start = _utc(start, "start")
        checked_end = _utc(end, "end")
        checked_now = _utc(now, "now")
        if checked_start is None or checked_end is None or checked_now is None:
            raise ValueError("Gap timestamps are required")
        schedule = await SqlSelectedSubscriptionIndexRepository(self.session)._writable_schedule(
            subscription_id, actor_id=actor_id, authorised_team_ids=authorised_team_ids
        )
        gate_id = await self.session.scalar(
            update(SelectedIndexGateRow)
            .where(SelectedIndexGateRow.id == 1)
            .values(revision=SelectedIndexGateRow.revision + 1)
            .returning(SelectedIndexGateRow.id)
        )
        if gate_id != 1:
            raise Conflict("Selected-index write gate is unavailable")
        await record_index_gap(
            self.session,
            subscription_id=subscription_id,
            owner_id=schedule.created_by,
            team_id=schedule.team_id,
            source_id=source_id,
            reason=reason,
            start=checked_start,
            end=checked_end,
            now=checked_now,
        )
