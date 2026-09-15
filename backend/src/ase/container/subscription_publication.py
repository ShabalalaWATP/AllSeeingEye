"""Publish a scheduled edition inside the report job's final transaction."""

from dataclasses import replace
from datetime import datetime
from uuid import UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.operational_models import ReportRow, ReportVersionRow, ScheduleRow
from ase.adapters.persistence.reports import SqlReportRepository
from ase.adapters.persistence.schedules import project_edition_outcome
from ase.adapters.persistence.subscription_comparisons import (
    SqlSubscriptionComparisonRepository,
)
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.access import AccessContext
from ase.application.reports.subscription_comparison import compare_subscription_versions
from ase.domain.errors import Conflict
from ase.domain.report_jobs import ReportJob
from ase.domain.report_records import ReportVersion
from ase.domain.reports import ReportStatus
from ase.domain.research_changes import change_from_dict
from ase.domain.schedules import CoverageState, ScheduleRunResult
from ase.domain.subscription_comparisons import EditionComparison
from ase.domain.subscription_editions import (
    EditionCoverage,
    EditionDelivery,
    EditionQuality,
    EditionWorkflow,
    ObservationInterval,
    SubscriptionEdition,
    SubscriptionLineage,
)

IN_APP_EVENT_NAMESPACE = UUID("79175739-234d-4fa0-9b3f-df151a23f053")


async def queue_in_app_change(
    session: AsyncSession,
    repository: SqlSubscriptionEditionRepository,
    edition: SubscriptionEdition,
    now: datetime,
) -> None:
    """Persist one opted-in change event in the edition publication transaction."""
    row = await session.get(ScheduleRow, edition.subscription_id, populate_existing=True)
    if row is None or not row.enabled or not row.notify_on_change:
        return
    change = change_from_dict(row.last_change)
    if change is None or change.status != "changed" or change.version_id != edition.version_id:
        return
    key = uuid5(IN_APP_EVENT_NAMESPACE, f"{edition.id}:material_change:in_app")
    await repository.add_delivery(
        EditionDelivery(
            id=key,
            edition_id=edition.id,
            channel="in_app",
            destination_ref=row.team_id or row.created_by,
            event_kind="material_change",
            idempotency_key=key,
            state="available",
            attempts=0,
            created_at=now,
            updated_at=now,
        )
    )


def merged_intervals(intervals: tuple[ObservationInterval, ...]) -> tuple[ObservationInterval, ...]:
    """Union adjacent half-open periods while retaining genuine gaps."""
    result: list[ObservationInterval] = []
    for current in sorted(intervals, key=lambda row: (row.start, row.end)):
        if result and current.start <= result[-1].end:
            previous = result[-1]
            result[-1] = ObservationInterval(previous.start, max(previous.end, current.end))
        else:
            result.append(current)
    return tuple(result)


def _complete_cutoff(
    intervals: tuple[ObservationInterval, ...], previous: datetime | None
) -> datetime | None:
    if not intervals:
        return previous
    cursor = previous or intervals[0].start
    for interval in intervals:
        if interval.start <= cursor < interval.end:
            cursor = interval.end
    return cursor


async def _advance_lineage(
    repository: SqlSubscriptionEditionRepository, edition: SubscriptionEdition, now: datetime
) -> None:
    if edition.gaps or merged_intervals(edition.effective_intervals) != (edition.requested,):
        return
    current = await repository.get_lineage(edition.subscription_id)
    if (
        current is not None
        and current.compatibility_fingerprint != edition.compatibility_fingerprint
    ):
        return  # A later substantive revision has its own baseline lineage.
    intervals = merged_intervals(
        (*current.covered_intervals, *edition.effective_intervals)
        if current is not None
        else edition.effective_intervals
    )
    baseline_id = edition.version_id
    if current is not None and current.analytical_baseline_version_id is not None:
        previous = await repository.get_by_version(current.analytical_baseline_version_id)
        if previous is not None and previous.requested.end > edition.requested.end:
            baseline_id = current.analytical_baseline_version_id
    lineage = SubscriptionLineage(
        subscription_id=edition.subscription_id,
        compatibility_fingerprint=edition.compatibility_fingerprint,
        analytical_baseline_version_id=baseline_id,
        covered_intervals=intervals,
        complete_cutoff=_complete_cutoff(
            intervals, current.complete_cutoff if current is not None else None
        ),
        updated_at=now,
        revision=current.revision + 1 if current is not None else 1,
    )
    saved = await repository.save_lineage(
        lineage, expected_revision=current.revision if current is not None else None
    )
    if saved is None:
        raise Conflict("Subscription lineage changed during report publication.")


async def _comparison_baseline(
    session: AsyncSession,
    edition: SubscriptionEdition,
    access: AccessContext,
    owner_id: UUID,
    team_id: UUID | None,
) -> ReportVersion | None:
    if edition.baseline_version_id is None:
        return None
    version_row = await session.get(
        ReportVersionRow, edition.baseline_version_id, populate_existing=True
    )
    if version_row is None:
        return None
    report = await session.get(ReportRow, version_row.report_id, populate_existing=True)
    if report is None:
        return None
    access.require_same_scope(owner_id, team_id, report.created_by, report.team_id)
    return await SqlReportRepository(session).get_version(report.id, version_row.number)


async def publish_subscription_edition(
    session: AsyncSession,
    stored: ReportJob,
    version: ReportVersion,
    access: AccessContext,
    now: datetime,
    *,
    research_required: bool,
) -> None:
    """Commit-free; caller saves report, job, edition and lineage together."""
    repository = SqlSubscriptionEditionRepository(session)
    edition = await repository.get_by_job(stored.id)
    if edition is None:
        return  # Ordinary one-off report job.
    access.require_write(stored.owner_id, stored.team_id)
    if edition.job_id != stored.id or (
        edition.report_id is not None and edition.report_id != version.report_id
    ):
        raise Conflict("Subscription edition and report job links do not match.")
    if edition.workflow is EditionWorkflow.COMPLETED:
        if edition.version_id == version.id:
            return
        raise Conflict("Subscription edition was published with another version.")
    if edition.workflow not in (EditionWorkflow.QUEUED, EditionWorkflow.RUNNING):
        raise Conflict("Subscription edition is no longer eligible for publication.")
    result = ScheduleRunResult.from_version(version, research_required=research_required)
    plan_complete = (
        result.coverage in (CoverageState.COMPLETE, CoverageState.NOT_APPLICABLE)
        and not edition.gaps
    )
    coverage = EditionCoverage.COMPLETE_FOR_PLAN if plan_complete else EditionCoverage.PARTIAL
    effective_intervals = edition.effective_intervals
    gaps = edition.gaps
    if plan_complete:
        effective_intervals = effective_intervals or (edition.requested,)
        gaps = ()
    elif not effective_intervals and not gaps:
        gaps = (edition.requested,)
    quality = (
        EditionQuality.READY
        if version.status is ReportStatus.READY
        else EditionQuality.NEEDS_REVIEW
        if version.status is ReportStatus.NEEDS_REVIEW
        else EditionQuality.FAILED
    )
    published = await repository.advance(
        replace(
            edition,
            workflow=EditionWorkflow.COMPLETED,
            report_quality=quality,
            coverage=coverage,
            effective_intervals=effective_intervals,
            gaps=gaps,
            report_id=version.report_id,
            version_id=version.id,
            updated_at=now,
            revision=edition.revision + 1,
            safe_reason=result.error_code.value if result.error_code is not None else None,
        ),
        expected_revision=edition.revision,
    )
    if published is None:
        raise Conflict("Subscription edition changed during report publication.")
    previous = await _comparison_baseline(
        session, published, access, stored.owner_id, stored.team_id
    )
    lineage = await repository.get_lineage(published.subscription_id)
    baseline_compatible = (
        lineage is None or lineage.compatibility_fingerprint == published.compatibility_fingerprint
    )
    comparison = EditionComparison(
        edition_id=published.id,
        previous_version_id=published.baseline_version_id,
        current_version_id=version.id,
        result=compare_subscription_versions(
            previous,
            version,
            coverage,
            baseline_expected=published.baseline_version_id is not None or lineage is not None,
            baseline_compatible=baseline_compatible,
        ),
        created_at=now,
    )
    await SqlSubscriptionComparisonRepository(session).add(comparison)
    projected = await project_edition_outcome(session, published, result, access)
    if (
        projected
        and quality is EditionQuality.READY
        and coverage is EditionCoverage.COMPLETE_FOR_PLAN
    ):
        await _advance_lineage(repository, published, now)
    if projected:
        await queue_in_app_change(session, repository, published, now)
