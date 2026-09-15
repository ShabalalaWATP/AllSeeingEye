"""Prepare a due edition and its report-job candidate outside admission locks."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.schedules import _from_row
from ase.adapters.persistence.subscription_briefs import load_schedule_brief
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.schedules.brief_link import standing_request_from_brief
from ase.application.schedules.edition_planning import DuePlan, plan_due_slots, window_for_slot
from ase.application.schedules.revision_snapshot import (
    request_from_revision,
    revision_from_schedule,
)
from ase.domain.errors import Conflict
from ase.domain.report_jobs import ReportJob
from ase.domain.schedules import Schedule
from ase.domain.subscription_editions import (
    EditionCoverage,
    EditionQuality,
    EditionTrigger,
    EditionWorkflow,
    ObservationInterval,
    SubscriptionEdition,
    SubscriptionRevision,
    manual_edition_id,
    scheduled_edition_id,
)

if TYPE_CHECKING:
    from ase.container import Container
    from ase.domain.users import User


class SubscriptionPreparation:
    container: Container

    async def _prepare_manual(
        self, schedule: Schedule, request_id: UUID, actor: User
    ) -> tuple[SubscriptionRevision, SubscriptionEdition, ReportJob, User]:
        """Freeze a requested run and prepare its job before taking admission locks."""
        async with self.container.session_factory() as session:
            row = await session.get(ScheduleRow, schedule.id)
            if row is None or _from_row(row) != schedule:
                raise Conflict("The subscription changed before manual admission.")
            access = await self.container.access_policy(session).context(actor)
            access.require_write(row.created_by, row.team_id)
            if not row.enabled:
                raise Conflict("Enable the subscription before running it.")
            owner_access = await self.container.access_policy(session).background(
                row.created_by, row.team_id
            )
            owner = owner_access.actor
            brief = await load_schedule_brief(session, owner_access, schedule)
            if brief is not None:
                standing_request_from_brief(brief, now=self.container.clock.now())
            ledger = SqlSubscriptionEditionRepository(session)
            latest = await ledger.latest_revision(schedule.id)
            now = self.container.clock.now()
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
            request = request_from_revision(frozen)
            lookback = timedelta(hours=request.window_hours or 24)
            window = window_for_slot(frozen, now, lookback, await ledger.get_lineage(schedule.id))
            # An explicit refresh may repeat a fully covered observation window.
            interval = window.interval or ObservationInterval(now - lookback, now)
            baseline = None
            if request.subscription_previous_report_id is not None:
                baseline = await self.container.repositories(session).reports.get_version(
                    request.subscription_previous_report_id, 1
                )
            edition = SubscriptionEdition(
                id=manual_edition_id(schedule.id, EditionTrigger.RUN_NOW, request_id),
                subscription_id=schedule.id,
                trigger=EditionTrigger.RUN_NOW,
                due_at_utc=None,
                request_uuid=request_id,
                frozen_revision=frozen.revision,
                requested=interval,
                effective_intervals=(),
                gaps=(),
                compatibility_fingerprint=frozen.compatibility_fingerprint,
                baseline_version_id=baseline.id if baseline is not None else None,
                workflow=EditionWorkflow.PENDING,
                report_quality=EditionQuality.ABSENT,
                coverage=EditionCoverage.UNKNOWN,
                created_at=now,
                updated_at=now,
            )
            request = replace(
                request,
                window_hours=None,
                research_since=interval.start,
                research_until=interval.end,
            )
            candidate = await self.container.report_jobs(session).prepare_candidate(
                owner, edition.job_request_key, request
            )
            if brief is not None:
                candidate = replace(
                    candidate, brief_id=brief.identity.id, brief_revision=brief.identity.revision
                )
            await session.rollback()
            return frozen, edition, candidate, owner

    async def _prepare(  # noqa: PLR0911, PLR0912, PLR0915
        self, *, schedule: Schedule | None, edition_id: UUID | None
    ) -> (
        tuple[
            SubscriptionRevision, SubscriptionEdition, ReportJob, User, DuePlan | None, UUID | None
        ]
        | None
    ):
        async with self.container.session_factory() as session:
            ledger = SqlSubscriptionEditionRepository(session)
            if edition_id is not None:
                edition = await ledger.get(edition_id)
                if edition is None or edition.workflow is not EditionWorkflow.PENDING:
                    return None
                frozen = await ledger.get_revision(edition.subscription_id, edition.frozen_revision)
                if frozen is None:
                    raise Conflict("The frozen subscription revision is unavailable.")
                row = await session.get(ScheduleRow, edition.subscription_id)
                plan = None
                superseded = None
            else:
                if schedule is None:
                    raise ValueError("A due schedule is required.")
                row = await session.get(ScheduleRow, schedule.id)
                if row is None or _from_row(row) != schedule:
                    return None
                now = self.container.clock.now()
                try:
                    plan = plan_due_slots(schedule, now)
                except ValueError as exc:
                    raise Conflict(str(exc)) from exc
                latest = await ledger.latest_revision(schedule.id)
                access = await self.container.access_policy(session).background(
                    row.created_by, row.team_id
                )
                brief = await load_schedule_brief(session, access, schedule)
                proposed = revision_from_schedule(
                    schedule,
                    latest.revision + 1 if latest else 1,
                    created_at=self.container.clock.now(),
                    brief=brief,
                )
                frozen = (
                    latest
                    if latest is not None
                    and latest.request_snapshot == proposed.request_snapshot
                    and latest.enabled == proposed.enabled
                    else proposed
                )
                active = await ledger.active(schedule.id)
                superseded = None
                if active is not None:
                    if (
                        active.due_at_utc == plan.latest
                        and active.workflow is EditionWorkflow.PENDING
                    ):
                        return await self._prepare(schedule=None, edition_id=active.id)
                    if (
                        active.workflow is not EditionWorkflow.PENDING
                        or active.job_id is not None
                        # A job-less manual edition waiting for capacity yields to the slot.
                        or (active.due_at_utc is not None and active.due_at_utc >= plan.latest)
                        or active.frozen_revision != frozen.revision
                        or active.compatibility_fingerprint != frozen.compatibility_fingerprint
                        or await ledger.attempts(active.id)
                    ):
                        return None
                    superseded = active.id
                request = request_from_revision(frozen)
                due = plan.latest
                hours = request.window_hours or 24
                window = window_for_slot(
                    frozen, due, timedelta(hours=hours), await ledger.get_lineage(schedule.id)
                )
                if window.covered_by_newer:
                    raise Conflict("A newer compatible edition covers this due slot.")
                interval = window.interval or ObservationInterval(due - timedelta(hours=hours), due)
                baseline = None
                if request.subscription_previous_report_id is not None:
                    baseline = await self.container.repositories(session).reports.get_version(
                        request.subscription_previous_report_id, 1
                    )
                edition = SubscriptionEdition(
                    id=scheduled_edition_id(schedule.id, due),
                    subscription_id=schedule.id,
                    trigger=EditionTrigger.CATCH_UP if plan.skipped else EditionTrigger.SCHEDULED,
                    due_at_utc=due,
                    request_uuid=None,
                    frozen_revision=frozen.revision,
                    requested=interval,
                    effective_intervals=(),
                    gaps=(),
                    compatibility_fingerprint=frozen.compatibility_fingerprint,
                    baseline_version_id=baseline.id if baseline is not None else None,
                    workflow=EditionWorkflow.PENDING,
                    report_quality=EditionQuality.ABSENT,
                    coverage=EditionCoverage.UNKNOWN,
                    created_at=now,
                    updated_at=now,
                )
            if row is None or not row.enabled:
                return None
            if (row.created_by, row.team_id) != (frozen.owner_id, frozen.team_id):
                return None
            access = await self.container.access_policy(session).background(
                row.created_by, row.team_id
            )
            actor = access.actor
            brief = await load_schedule_brief(session, access, _from_row(row))
            if brief is not None:
                standing_request_from_brief(brief, now=self.container.clock.now())
            request = request_from_revision(frozen)
            request = replace(
                request,
                window_hours=None,
                research_since=edition.requested.start,
                research_until=edition.requested.end,
            )
            candidate = await self.container.report_jobs(session).prepare_candidate(
                actor, edition.job_request_key, request
            )
            if brief is not None:
                candidate = replace(
                    candidate, brief_id=brief.identity.id, brief_revision=brief.identity.revision
                )
            await session.rollback()
            return frozen, edition, candidate, actor, plan, superseded
