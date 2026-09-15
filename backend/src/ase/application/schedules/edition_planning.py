"""Bounded calendar catch-up and frozen subscription observation windows."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import UUID

from ase.domain.schedules import Schedule
from ase.domain.subscription_editions import (
    EditionTrigger,
    EditionWorkflow,
    ObservationInterval,
    SubscriptionEdition,
    SubscriptionLineage,
    SubscriptionRevision,
    scheduled_edition_id,
)
from ase.domain.subscription_recurrence import RequestedWindow, WindowPolicy, requested_window

MAX_COALESCED_SLOTS = 366


@dataclass(frozen=True, slots=True)
class DuePlan:
    due_slots: tuple[datetime, ...]
    next_run_at: datetime

    @property
    def latest(self) -> datetime:
        return self.due_slots[-1]

    @property
    def skipped(self) -> tuple[datetime, ...]:
        return self.due_slots[:-1]


def plan_due_slots(schedule: Schedule, now: datetime) -> DuePlan:
    """Coalesce missed local calendar slots into a single latest due edition.

    Refuse more than one year of daily history for automatic recovery rather
    than silently omit unsearched slots. The operator can perform a backfill.
    """
    if schedule.next_run_at > now:
        raise ValueError("The subscription has no due slot.")
    slots = [schedule.next_run_at]
    for _ in range(MAX_COALESCED_SLOTS):
        next_at = schedule.recurrence.preview(slots[-1], 1)[0].utc
        if next_at > now:
            return DuePlan(tuple(slots), next_at)
        slots.append(next_at)
    raise ValueError("Automatic catch-up exceeds 366 missed calendar slots.")


def window_for_slot(
    revision: SubscriptionRevision,
    due_at: datetime,
    lookback: timedelta,
    lineage: SubscriptionLineage | None,
) -> RequestedWindow:
    """Use only a compatible complete cutoff, never a partial analytical baseline."""
    policy = WindowPolicy(revision.collection_policy.removesuffix("_v1"))
    cutoff = (
        lineage.complete_cutoff
        if lineage is not None
        and lineage.compatibility_fingerprint == revision.compatibility_fingerprint
        else None
    )
    return requested_window(policy, due_at, lookback, compatible_complete_cutoff=cutoff)


def coalesced_edition(
    old: SubscriptionEdition, covering_id: UUID, now: datetime
) -> SubscriptionEdition:
    return replace(
        old,
        workflow=EditionWorkflow.SKIPPED,
        gaps=(old.requested,),
        safe_reason="coalesced_catch_up",
        covered_by_edition_id=covering_id,
        updated_at=now,
        revision=old.revision + 1,
    )


def missed_edition(
    covering: SubscriptionEdition, due: datetime, requested: ObservationInterval
) -> SubscriptionEdition:
    return replace(
        covering,
        id=scheduled_edition_id(covering.subscription_id, due),
        trigger=EditionTrigger.SCHEDULED,
        due_at_utc=due,
        requested=requested,
        workflow=EditionWorkflow.PENDING,
    )


def admission_wait(
    edition: SubscriptionEdition, now: datetime, *, budget_exhausted: bool
) -> SubscriptionEdition:
    return replace(
        edition,
        workflow=EditionWorkflow.BLOCKED if budget_exhausted else EditionWorkflow.PENDING,
        safe_reason="monthly_budget_exhausted" if budget_exhausted else "capacity_wait",
        updated_at=now,
        revision=edition.revision + 1,
    )
