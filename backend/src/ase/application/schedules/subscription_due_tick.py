"""Bounded, fair polling of due subscriptions and waiting editions."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from ase.application.ports.services import Clock
from ase.application.ports.subscription_admission import (
    SubscriptionDueQueue,
)
from ase.application.schedules.edition_planning import plan_due_slots
from ase.application.schedules.runner import DueCursor
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound, RateLimited
from ase.domain.research_brief_values import BriefValidationError
from ase.domain.schedules import Schedule

log = logging.getLogger(__name__)
SCHEDULE_DUE_LIMIT = 16
PENDING_DUE_LIMIT = 16


class SubscriptionDueTick:
    due: SubscriptionDueQueue
    clock: Clock
    _schedule_cursor: DueCursor | None
    _pending_cursor: DueCursor | None

    if TYPE_CHECKING:

        async def enqueue(
            self, *, schedule: Schedule | None = None, edition_id: UUID | None = None
        ) -> bool: ...

    async def tick(self) -> int:
        now = self.clock.now()
        due, self._schedule_cursor = await self.due.schedules(
            now, limit=SCHEDULE_DUE_LIMIT, cursor=self._schedule_cursor
        )
        pending, self._pending_cursor = await self.due.editions(
            now, limit=PENDING_DUE_LIMIT, cursor=self._pending_cursor
        )
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
