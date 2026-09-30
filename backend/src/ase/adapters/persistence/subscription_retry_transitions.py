"""Fenced closure of a due subscription retry without altering paid calls."""

from dataclasses import replace
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.domain.report_jobs import ReportJob
from ase.domain.subscription_editions import EditionWorkflow, SubscriptionEdition


async def stop_waiting(
    session: AsyncSession,
    edition: SubscriptionEdition,
    job: ReportJob,
    workflow: EditionWorkflow,
    reason: str,
    now: datetime,
) -> bool:
    """Apply both revision fences in the caller's transaction."""
    changed = await session.scalar(
        update(ReportJobRow)
        .where(
            ReportJobRow.id == job.id,
            ReportJobRow.revision == job.revision,
            ReportJobRow.status == "paused",
            ReportJobRow.error == "known_transient_failure",
        )
        .values(
            status="failed" if workflow is EditionWorkflow.FAILED else "paused",
            stage="failed" if workflow is EditionWorkflow.FAILED else "paused",
            error=reason,
            updated_at=now,
            revision=ReportJobRow.revision + 1,
        )
        .returning(ReportJobRow.id)
        .execution_options(synchronize_session=False)
    )
    if changed is None:
        return False
    advanced = await SqlSubscriptionEditionRepository(session).advance(
        replace(
            edition,
            workflow=workflow,
            safe_reason=reason,
            updated_at=now,
            revision=edition.revision + 1,
        ),
        expected_revision=edition.revision,
    )
    return advanced is not None
