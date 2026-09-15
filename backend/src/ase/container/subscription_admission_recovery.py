"""Fenced recovery that keeps waiting or long-overdue subscriptions admissible."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import UUID

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.schedules import _from_row
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.edition_planning import (
    budget_retry_due,
    rebased_next_run,
    reopened_for_admission,
)
from ase.domain.schedules import Schedule

if TYPE_CHECKING:
    from ase.container import Container

log = logging.getLogger(__name__)


async def reopen_budget_block(
    container: Container, *, schedule_id: UUID | None, edition_id: UUID | None
) -> None:
    """Return a job-less budget block to pending once its retry delay has passed."""
    now = container.clock.now()
    async with container.source_admission.guard(), container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        if edition_id is not None:
            edition = await ledger.get(edition_id)
        elif schedule_id is not None:
            edition = await ledger.active(schedule_id)
        else:
            return
        if edition is None or not budget_retry_due(edition, now):
            return
        reopened = reopened_for_admission(edition, now)
        if await ledger.advance(reopened, expected_revision=edition.revision) is None:
            await session.rollback()
            return
        await session.commit()


async def rebase_overdue(container: Container, schedule: Schedule) -> Schedule | None:
    """Skip unrecoverable history to the latest slot; None when the schedule changed."""
    now = container.clock.now()
    rebased = rebased_next_run(schedule, now)
    if rebased is None:
        return schedule
    async with container.source_admission.guard(), container.session_factory() as session:
        row = await session.get(ScheduleRow, schedule.id, populate_existing=True)
        if row is None or not row.enabled or _from_row(row) != schedule:
            return None
        row.next_run_at = rebased
        await session.commit()
    log.warning("subscription_catch_up_skipped_ahead")
    return replace(schedule, next_run_at=rebased)
