"""Bounded, fair polling of due subscriptions and waiting editions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from ase.adapters.persistence.schedules import SqlScheduleStore
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.edition_planning import plan_due_slots
from ase.application.schedules.runner import DueCursor
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound, RateLimited
from ase.domain.research_brief_values import BriefValidationError
from ase.domain.schedules import Schedule

if TYPE_CHECKING:
    from ase.container import Container

log = logging.getLogger(__name__)
SCHEDULE_DUE_LIMIT = 16
PENDING_DUE_LIMIT = 16


class SubscriptionDueTick:
    container: Container
    _schedule_cursor: DueCursor | None
    _pending_cursor: DueCursor | None

    if TYPE_CHECKING:

        async def enqueue(
            self, *, schedule: Schedule | None = None, edition_id: UUID | None = None
        ) -> bool: ...

    async def tick(self) -> int:
        now = self.container.clock.now()
        store = SqlScheduleStore(self.container.session_factory, self.container.access_policy)
        due, self._schedule_cursor = await store.due_batch(
            now, limit=SCHEDULE_DUE_LIMIT, cursor=self._schedule_cursor
        )
        async with self.container.session_factory() as session:
            pending_rows, self._pending_cursor = await SqlSubscriptionEditionRepository(
                session
            ).due_batch(now, limit=PENDING_DUE_LIMIT, cursor=self._pending_cursor)
        pending = [edition for edition, _ in pending_rows]
        count = 0
        for schedule in due:
            if await self._safe_enqueue(schedule=schedule):
                count += 1
        due_latest = {}
        for item in due:
            try:
                due_latest[item.id] = plan_due_slots(item, now).latest
            except ValueError:
                continue
        for edition in pending:
            # Manual editions have no slot; a matching slot is handled by its schedule.
            scheduled_here = edition.due_at_utc is not None and edition.due_at_utc == (
                due_latest.get(edition.subscription_id)
            )
            if not scheduled_here and await self._safe_enqueue(edition_id=edition.id):
                count += 1
        return count

    async def _safe_enqueue(
        self, *, schedule: Schedule | None = None, edition_id: UUID | None = None
    ) -> bool:
        try:
            return await self.enqueue(schedule=schedule, edition_id=edition_id)
        except (BriefValidationError, Conflict, Forbidden, InvalidRequest, NotFound, RateLimited):
            log.warning("subscription_admission_blocked")
            return False
        except Exception:
            # Provider and source exception text can contain private inputs.
            log.warning("subscription_admission_failed")
            return False
