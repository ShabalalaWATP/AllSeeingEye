"""Read-only, bounded subscription and report-queue health aggregates."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionEditionRow
from ase.application.report_jobs.controls import MAX_OPEN_GLOBAL
from ase.application.schedules.diagnostics import SubscriptionDiagnostics
from ase.domain.subscription_editions import ACTIVE_WORKFLOWS, EditionWorkflow

SOURCE_FAILURE_CODES = ("source_failure_coverage", "source_disabled")


async def subscription_diagnostics(
    session: AsyncSession, *, now: datetime
) -> SubscriptionDiagnostics:
    """Count saved states only; a safe reason is not a live provider health probe."""
    observed = now.astimezone(UTC)
    enabled = await session.scalar(
        select(func.count()).select_from(ScheduleRow).where(ScheduleRow.enabled.is_(True))
    )
    due = await session.execute(
        select(func.count(), func.min(ScheduleRow.next_run_at)).where(
            ScheduleRow.enabled.is_(True), ScheduleRow.next_run_at <= observed
        )
    )
    overdue, oldest = due.one()
    counts = await session.execute(
        select(SubscriptionEditionRow.workflow, func.count())
        .where(SubscriptionEditionRow.workflow.in_(tuple(item.value for item in ACTIVE_WORKFLOWS)))
        .group_by(SubscriptionEditionRow.workflow)
    )
    active = {item.value: 0 for item in ACTIVE_WORKFLOWS}
    for workflow, count in counts.all():
        active[workflow] = count
    uncertain = await session.scalar(
        select(func.count())
        .select_from(SubscriptionEditionRow)
        .where(
            SubscriptionEditionRow.workflow == EditionWorkflow.PAUSED.value,
            SubscriptionEditionRow.safe_reason == "uncertain_paid_outcome",
        )
    )
    source_rows = await session.execute(
        select(SubscriptionEditionRow.safe_reason, func.count())
        .where(SubscriptionEditionRow.safe_reason.in_(SOURCE_FAILURE_CODES))
        .group_by(SubscriptionEditionRow.safe_reason)
    )
    source_categories = dict.fromkeys(SOURCE_FAILURE_CODES, 0)
    for reason, count in source_rows.all():
        source_categories[reason] = count
    admitted = await session.scalar(
        select(func.max(ReportJobRow.created_at))
        .select_from(SubscriptionEditionRow)
        .join(ReportJobRow, SubscriptionEditionRow.job_id == ReportJobRow.id)
    )
    open_jobs = await session.scalar(
        select(func.count())
        .select_from(ReportJobRow)
        .where(ReportJobRow.status.in_(("queued", "running", "paused")))
    )
    lag = max(0, int((observed - oldest).total_seconds())) if oldest is not None else None
    return SubscriptionDiagnostics(
        observed_at=observed,
        enabled_subscriptions=enabled or 0,
        overdue_subscriptions=overdue or 0,
        oldest_due_at=oldest,
        oldest_due_lag_seconds=lag,
        active_editions_by_workflow=active,
        uncertain_outcome_editions=uncertain or 0,
        source_failure_editions=sum(source_categories.values()),
        source_failure_categories=source_categories,
        last_admitted_job_at=admitted,
        open_report_jobs=open_jobs or 0,
        global_open_job_limit=MAX_OPEN_GLOBAL,
        queue_saturated=(open_jobs or 0) >= MAX_OPEN_GLOBAL,
    )
