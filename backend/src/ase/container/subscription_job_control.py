"""Keep a subscription edition aligned with explicit report-job controls."""

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.report_jobs.service import EditionAction
from ase.domain.errors import Conflict, InvalidRequest
from ase.domain.subscription_editions import EditionWorkflow


async def control_subscription_job(
    session: AsyncSession, job_id: UUID, action: EditionAction, now: datetime
) -> None:
    """Commit-free; the caller owns the same transaction as the job transition."""
    repository = SqlSubscriptionEditionRepository(session)
    edition = await repository.get_by_job(job_id)
    if edition is None:
        return
    if action == "discard":
        raise InvalidRequest(
            "A subscription edition keeps its report progress and usage history. "
            "Pause the subscription or use its edition controls."
        )
    if action == "pause":
        if edition.workflow is EditionWorkflow.PAUSED:
            return
        if edition.workflow not in (EditionWorkflow.QUEUED, EditionWorkflow.RUNNING):
            raise Conflict("The subscription edition cannot be paused from its current state.")
        workflow = EditionWorkflow.PAUSED
        safe_reason = "operator_paused"
    else:
        if edition.workflow in (EditionWorkflow.QUEUED, EditionWorkflow.RUNNING):
            return
        if edition.workflow not in (
            EditionWorkflow.PAUSED,
            EditionWorkflow.BLOCKED,
            EditionWorkflow.RETRY_WAIT,
        ):
            raise Conflict("The subscription edition cannot be resumed from its current state.")
        workflow = EditionWorkflow.QUEUED
        safe_reason = None
    updated = await repository.advance(
        replace(
            edition,
            workflow=workflow,
            safe_reason=safe_reason,
            updated_at=now,
            revision=edition.revision + 1,
        ),
        expected_revision=edition.revision,
    )
    if updated is None:
        raise Conflict("The subscription edition changed during the job control request.")
