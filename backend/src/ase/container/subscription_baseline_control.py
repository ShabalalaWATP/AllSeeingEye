"""Explicitly accept a limited edition for analytical comparison only."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_briefs import load_schedule_brief
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.dto import RequestContext
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import TEMPLATES
from ase.application.schedules.revision_snapshot import (
    request_from_revision,
    revision_from_schedule,
)
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, NotFound
from ase.domain.reports import ReportStatus
from ase.domain.research_brief_values import BriefValidationError
from ase.domain.schedules import CoverageState, ScheduleRunResult
from ase.domain.subscription_editions import (
    EditionCoverage,
    EditionQuality,
    EditionWorkflow,
    SubscriptionEdition,
    SubscriptionLineage,
    SubscriptionRevision,
)

if TYPE_CHECKING:
    from ase.container import Container
    from ase.domain.schedules import Schedule
    from ase.domain.users import User


def _eligible(edition: SubscriptionEdition) -> bool:
    return (
        edition.workflow is EditionWorkflow.COMPLETED
        and edition.report_quality in {EditionQuality.READY, EditionQuality.NEEDS_REVIEW}
        and (
            edition.report_quality is EditionQuality.NEEDS_REVIEW
            or edition.coverage is EditionCoverage.PARTIAL
        )
        and edition.job_id is not None
        and edition.report_id is not None
        and edition.version_id is not None
    )


async def _verify_provenance(
    container: Container,
    session: AsyncSession,
    schedule: Schedule,
    edition: SubscriptionEdition,
    frozen: SubscriptionRevision,
) -> None:
    """Require exact durable job, report, version, period and originating scope links."""
    if edition.job_id is None or edition.report_id is None or edition.version_id is None:
        raise Conflict("The saved edition has no complete report provenance.")
    job = await SqlReportJobRepository(session).get(edition.job_id)
    report = await container.repositories(session).reports.get(edition.report_id)
    if job is None or report is None:
        raise Conflict("The saved edition provenance is unavailable.")
    expected_status = (
        "needs_review" if edition.report_quality is EditionQuality.NEEDS_REVIEW else "completed"
    )
    try:
        request = request_from_revision(frozen)
        scope = report_scope(request, TEMPLATES[request.template_id])
    except (KeyError, ValueError) as exc:
        raise Conflict("The frozen subscription request is unavailable.") from exc
    stable_scope = {
        key: value
        for key, value in scope.items()
        if key not in {"research_since", "research_until", "window_hours"}
    }
    if (
        job.request_key != edition.job_request_key
        or (job.owner_id, job.team_id) != (schedule.created_by, schedule.team_id)
        or (job.report_id, job.version_id) != (edition.report_id, edition.version_id)
        or job.status != expected_status
        or (report.created_by, report.team_id) != (schedule.created_by, schedule.team_id)
        or report.template != request.template_id
        or report.latest_version != 1
        or (report.period_from, report.period_to)
        != (edition.requested.start, edition.requested.end)
        or any(report.scope.get(key) != value for key, value in stable_scope.items())
    ):
        raise Conflict("The saved edition provenance no longer matches its subscription.")
    version = await container.repositories(session).reports.get_version(report.id, 1)
    expected_quality = (
        EditionQuality.NEEDS_REVIEW
        if version is not None and version.status is ReportStatus.NEEDS_REVIEW
        else EditionQuality.READY
    )
    if (
        version is None
        or version.id != edition.version_id
        or version.report_id != report.id
        or version.status not in {ReportStatus.READY, ReportStatus.NEEDS_REVIEW}
        or version.status != report.status
        or expected_quality is not edition.report_quality
        or (version.period_from, version.period_to)
        != (edition.requested.start, edition.requested.end)
        or (version.brief_id, version.brief_revision)
        != (schedule.brief_id, schedule.brief_revision)
        or not version.evidence
    ):
        raise Conflict("The saved report version no longer matches its edition.")
    result = ScheduleRunResult.from_version(
        version, research_required=schedule.research_mode is not None
    )
    expected_coverage = (
        EditionCoverage.COMPLETE_FOR_PLAN
        if result.coverage in {CoverageState.COMPLETE, CoverageState.NOT_APPLICABLE}
        and not edition.gaps
        else EditionCoverage.PARTIAL
    )
    if expected_coverage is not edition.coverage:
        raise Conflict("The saved report coverage no longer matches its edition.")


async def _save_analytical_lineage(
    ledger: SqlSubscriptionEditionRepository, edition: SubscriptionEdition, now: datetime
) -> tuple[SubscriptionLineage, bool]:
    current = await ledger.get_lineage(edition.subscription_id)
    if (
        current is not None
        and current.compatibility_fingerprint != edition.compatibility_fingerprint
    ):
        raise Conflict("The current subscription lineage is incompatible.")
    if edition.accepted_as_baseline:
        if current is None or current.analytical_baseline_version_id != edition.version_id:
            raise Conflict("A newer analytical baseline replaced this accepted edition.")
        return current, False
    if current is not None and current.analytical_baseline_version_id is not None:
        previous = await ledger.get_by_version(current.analytical_baseline_version_id)
        if previous is None or previous.requested.end > edition.requested.end:
            raise Conflict("A newer or unverified analytical baseline already exists.")
    lineage = (
        replace(
            current,
            analytical_baseline_version_id=edition.version_id,
            updated_at=now,
            revision=current.revision + 1,
        )
        if current is not None
        else SubscriptionLineage(
            subscription_id=edition.subscription_id,
            compatibility_fingerprint=edition.compatibility_fingerprint,
            analytical_baseline_version_id=edition.version_id,
            covered_intervals=(),
            complete_cutoff=None,
            updated_at=now,
        )
    )
    saved = (
        current
        if current is not None and current.analytical_baseline_version_id == edition.version_id
        else await ledger.save_lineage(
            lineage, expected_revision=current.revision if current is not None else None
        )
    )
    if saved is None:
        raise Conflict("Subscription lineage changed during baseline acceptance.")
    return saved, True


async def accept_baseline(
    container: Container,
    session: AsyncSession,
    actor: User,
    schedule_id: UUID,
    edition_id: UUID,
    context: RequestContext,
    *,
    check_session: Callable[[], Awaitable[None]],
) -> SubscriptionLineage:
    """Commit one audited comparison choice without claiming unsearched dates."""
    await check_session()
    async with container.source_admission.guard():
        try:
            repos = container.repositories(session)
            access = await container.access_policy(session).context(actor, for_update=True)
            schedule = await repos.schedules.get(schedule_id)
            if schedule is None:
                raise NotFound("Subscription not found.")
            access.require_write(schedule.created_by, schedule.team_id)
            ledger = SqlSubscriptionEditionRepository(session)
            edition = await ledger.get(edition_id)
            if edition is None or edition.subscription_id != schedule_id:
                raise NotFound("Subscription edition not found.")
            if not _eligible(edition):
                raise Conflict("Only a completed needs-review or partial edition can be accepted.")
            frozen = await ledger.get_revision(schedule_id, edition.frozen_revision)
            brief = await load_schedule_brief(session, access, schedule)
            if brief is not None:
                try:
                    brief.require_subscription_ready(now=container.clock.now())
                except BriefValidationError as exc:
                    raise Conflict("The linked Research Brief is no longer ready.") from exc
            if (
                frozen is None
                or (frozen.owner_id, frozen.team_id) != (schedule.created_by, schedule.team_id)
                or frozen.compatibility_fingerprint != edition.compatibility_fingerprint
                or revision_from_schedule(schedule, 1, brief=brief).compatibility_fingerprint
                != edition.compatibility_fingerprint
            ):
                raise Conflict("The subscription definition changed since this edition.")
            await _verify_provenance(container, session, schedule, edition, frozen)
            now = container.clock.now()
            saved, changed = await _save_analytical_lineage(ledger, edition, now)
            if not changed:
                await check_session()
                return saved
            accepted = await ledger.advance(
                replace(
                    edition,
                    accepted_as_baseline=True,
                    updated_at=now,
                    revision=edition.revision + 1,
                ),
                expected_revision=edition.revision,
            )
            if accepted is None:
                raise Conflict("Subscription edition changed during baseline acceptance.")
            await container._auditor(repos).record(
                AuditAction.SCHEDULE_UPDATED,
                actor=actor.id,
                subject=str(schedule_id),
                ip=context.ip,
                details={
                    "action": "accept_baseline",
                    "edition_id": str(edition.id),
                    "version_id": str(edition.version_id),
                    "quality": edition.report_quality.value,
                    "coverage": edition.coverage.value,
                },
            )
            await check_session()
            await repos.uow.commit()
            return saved
        except BaseException:
            await session.rollback()
            raise
