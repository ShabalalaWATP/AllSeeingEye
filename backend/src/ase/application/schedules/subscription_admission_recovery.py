"""Fenced recovery that keeps waiting or long-overdue subscriptions admissible."""

from __future__ import annotations

import logging
from dataclasses import replace
from uuid import UUID

from ase.application.ports.services import Clock
from ase.application.ports.subscription_admission import (
    SourceGuard,
    SubscriptionTransactions,
)
from ase.application.schedules.edition_planning import (
    budget_retry_due,
    rebased_next_run,
    reopened_for_admission,
)
from ase.domain.schedules import Schedule

log = logging.getLogger(__name__)


async def reopen_budget_block(
    transactions: SubscriptionTransactions,
    clock: Clock,
    guard: SourceGuard,
    *,
    schedule_id: UUID | None,
    edition_id: UUID | None,
) -> None:
    """Return a job-less budget block to pending once its retry delay has passed."""
    now = clock.now()
    async with guard(), transactions() as session:
        ledger = session.ledger
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


async def rebase_overdue(
    transactions: SubscriptionTransactions, clock: Clock, guard: SourceGuard, schedule: Schedule
) -> Schedule | None:
    """Skip unrecoverable history to the latest slot; None when the schedule changed."""
    now = clock.now()
    rebased = rebased_next_run(schedule, now)
    if rebased is None:
        return schedule
    async with guard(), transactions() as session:
        row = await session.schedule(schedule.id, refresh=True)
        if row is None or not row.enabled or row != schedule:
            return None
        await session.advance_schedule(row.id, rebased)
        await session.commit()
    log.warning("subscription_catch_up_skipped_ahead")
    return replace(schedule, next_run_at=rebased)
