"""Commit-free coalescing transitions and covered-slot recovery."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.schedules import _from_row
from ase.adapters.persistence.subscription_briefs import load_schedule_brief
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.brief_link import standing_request_from_brief
from ase.application.schedules.edition_planning import (
    DuePlan,
    coalesced_edition,
    missed_edition,
    plan_due_slots,
    window_for_slot,
)
from ase.application.schedules.revision_snapshot import (
    request_from_revision,
    revision_from_schedule,
)
from ase.domain.errors import Conflict
from ase.domain.schedules import Schedule
from ase.domain.subscription_editions import (
    EditionCoverage,
    EditionQuality,
    EditionTrigger,
    EditionWorkflow,
    ObservationInterval,
    SubscriptionEdition,
    SubscriptionRevision,
    scheduled_edition_id,
)

if TYPE_CHECKING:
    from ase.container import Container


async def skip_unstarted(
    ledger: SqlSubscriptionEditionRepository,
    old: SubscriptionEdition,
    covering_id: UUID,
    now: datetime,
) -> bool:
    if (
        old.workflow is not EditionWorkflow.PENDING
        or old.job_id is not None
        or await ledger.attempts(old.id)
    ):
        return False
    skipped = coalesced_edition(old, covering_id, now)
    return await ledger.advance(skipped, expected_revision=old.revision) is not None


async def record_skipped(
    ledger: SqlSubscriptionEditionRepository,
    covering: SubscriptionEdition,
    plan: DuePlan,
    frozen: SubscriptionRevision,
    now: datetime,
) -> None:
    lookback = timedelta(hours=request_from_revision(frozen).window_hours or 24)
    lineage = await ledger.get_lineage(covering.subscription_id)
    for due in plan.skipped:
        identity = scheduled_edition_id(covering.subscription_id, due)
        if await ledger.get(identity) is not None:
            continue
        window = window_for_slot(frozen, due, lookback, lineage)
        interval = window.interval or ObservationInterval(due - lookback, due)
        covering_id = covering.id
        if window.covered_by_newer and lineage is not None:
            older_cover = (
                await ledger.get_by_version(lineage.analytical_baseline_version_id)
                if lineage.analytical_baseline_version_id is not None
                else None
            )
            if older_cover is not None:
                covering_id = older_cover.id
        old = missed_edition(covering, due, interval)
        reserved = await ledger.reserve(old)
        if not await skip_unstarted(ledger, reserved, covering_id, now):
            raise Conflict("A missed subscription slot has already started.")


async def skip_covered_due(container: Container, schedule: Schedule) -> bool:
    """Advance a fully covered old slot without preparing or charging a job."""
    now = container.clock.now()
    async with container.source_admission.guard(), container.session_factory() as session:
        ledger = SqlSubscriptionEditionRepository(session)
        row = await session.get(ScheduleRow, schedule.id, populate_existing=True)
        if row is None or not row.enabled or _from_row(row) != schedule:
            return False
        access = await container.access_policy(session).background(
            row.created_by, row.team_id, for_update=True
        )
        row = await session.get(ScheduleRow, schedule.id, populate_existing=True)
        if row is None or not row.enabled or _from_row(row) != schedule:
            return False
        plan = plan_due_slots(schedule, now)
        latest = await ledger.latest_revision(schedule.id)
        brief = await load_schedule_brief(session, access, schedule)
        if brief is not None:
            standing_request_from_brief(brief, now=now)
        proposed = revision_from_schedule(
            schedule, latest.revision + 1 if latest else 1, created_at=now, brief=brief
        )
        frozen = (
            latest
            if latest is not None
            and latest.request_snapshot == proposed.request_snapshot
            and latest.enabled == proposed.enabled
            else proposed
        )
        lineage = await ledger.get_lineage(schedule.id)
        if (
            lineage is None
            or lineage.compatibility_fingerprint != frozen.compatibility_fingerprint
            or lineage.complete_cutoff is None
            or lineage.complete_cutoff < plan.latest
            or lineage.analytical_baseline_version_id is None
        ):
            return False
        covering = await ledger.get_by_version(lineage.analytical_baseline_version_id)
        if covering is None or covering.requested.end < plan.latest:
            return False
        if latest is None or latest.revision < frozen.revision:
            await ledger.add_revision(frozen)
        active = await ledger.active(schedule.id)
        if active is not None and (
            active.compatibility_fingerprint != frozen.compatibility_fingerprint
            or not await skip_unstarted(ledger, active, covering.id, now)
        ):
            return False
        lookback = timedelta(hours=request_from_revision(frozen).window_hours or 24)
        for due in plan.due_slots:
            identity = scheduled_edition_id(schedule.id, due)
            if await ledger.get(identity) is not None:
                continue
            interval = ObservationInterval(due - lookback, due)
            pending = SubscriptionEdition(
                id=identity,
                subscription_id=schedule.id,
                trigger=EditionTrigger.SCHEDULED,
                due_at_utc=due,
                request_uuid=None,
                frozen_revision=frozen.revision,
                requested=interval,
                effective_intervals=(),
                gaps=(),
                compatibility_fingerprint=frozen.compatibility_fingerprint,
                baseline_version_id=None,
                workflow=EditionWorkflow.PENDING,
                report_quality=EditionQuality.ABSENT,
                coverage=EditionCoverage.UNKNOWN,
                created_at=now,
                updated_at=now,
            )
            reserved = await ledger.reserve(pending)
            if not await skip_unstarted(ledger, reserved, covering.id, now):
                raise Conflict("A covered subscription slot has already started.")
        row.next_run_at = plan.next_run_at
        await session.commit()
        return True
