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
from ase.domain.subscription_recurrence import (
    LocalRecurrence,
    RequestedWindow,
    WindowPolicy,
    requested_window,
)

MAX_COALESCED_SLOTS = 366
# Search spans comfortably exceed each cadence's longest gap (daily to annual).
_SLOT_SEARCH_DAYS = (2, 8, 33, 94, 186, 368, 734)


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


def latest_slot_at_or_before(recurrence: LocalRecurrence, now: datetime) -> datetime | None:
    """Find the most recent calendar slot without walking the whole missed history."""
    for days in _SLOT_SEARCH_DAYS:
        cursor = now - timedelta(days=days)
        latest = None
        for _ in range(MAX_COALESCED_SLOTS):
            occurrence = recurrence.preview(cursor, 1)[0].utc
            if occurrence > now:
                break
            latest = cursor = occurrence
        if latest is not None:
            return latest
    return None


def rebased_next_run(schedule: Schedule, now: datetime) -> datetime | None:
    """Skip ahead to the latest due slot once automatic catch-up exceeds its bound.

    Returns None when the stored due slot is in the future or still recoverable.
    """
    if schedule.next_run_at > now:
        return None
    try:
        plan_due_slots(schedule, now)
    except ValueError:
        return latest_slot_at_or_before(schedule.recurrence, now)
    return None


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
