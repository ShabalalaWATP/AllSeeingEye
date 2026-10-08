"""Hourly admission probe for subscription editions blocked on a retained job.

A budget or allowance block can clear on its own: a UTC month rolls over, an
administrator raises an allowance or other work frees the owner's monthly budget.
Without a probe the blocked edition stays the subscription's active edition and no
later edition is admitted. The probe resumes the same saved job under the same
admission checks as a manual resume; it never creates a fresh edition or job.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from ase.application.ports import Clock
from ase.application.ports.subscription_admission import SourceGuard
from ase.application.ports.subscription_retry import (
    SubscriptionRetrySession,
    SubscriptionRetryTransactions,
)
from ase.application.report_jobs.budget import JobInterrupted
from ase.application.report_jobs.controls import require_capacity, resumed_payload
from ase.application.report_jobs.views import refresh_summary
from ase.application.schedules.subscription_admission_wait import (
    BUDGET_RETRY_AFTER,
    JOB_BLOCK_REASONS,
)
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.report_jobs import ReportJob
from ase.domain.subscription_editions import EditionWorkflow, SubscriptionEdition


async def resume_blocked(
    transactions: SubscriptionRetryTransactions, clock: Clock, guard: SourceGuard
) -> None:
    now = clock.now()
    async with transactions() as session:
        due = await session.due_blocked_ids(now)
    for edition_id in due:
        # Match schedule controls: source guard, then the DB administration guard.
        async with guard(), transactions() as session:
            await session.lock_administration()
            await _probe(session, edition_id, now)


def _due(edition: SubscriptionEdition | None, now: datetime) -> bool:
    return (
        edition is not None
        and edition.workflow is EditionWorkflow.BLOCKED
        and edition.job_id is not None
        and edition.safe_reason in JOB_BLOCK_REASONS
        and now - edition.updated_at >= BUDGET_RETRY_AFTER
    )


async def _blocked_job(
    session: SubscriptionRetrySession, edition_id: UUID, now: datetime
) -> tuple[SubscriptionEdition, ReportJob] | None:
    edition = await session.editions.get(edition_id)
    if edition is None or edition.job_id is None or not _due(edition, now):
        return None
    schedule = await session.schedules.get(edition.subscription_id)
    if schedule is None or not schedule.enabled or schedule.archived_at is not None:
        return None
    job = await session.jobs.get(edition.job_id)
    if job is None or job.status != "paused":
        return None
    return edition, job


async def _commit_if(session: SubscriptionRetrySession, applied: bool) -> None:
    if applied:
        await session.commit()
    else:
        await session.rollback()


async def _probe(session: SubscriptionRetrySession, edition_id: UUID, now: datetime) -> None:
    found = await _blocked_job(session, edition_id, now)
    if found is None:
        return
    edition, job = found
    try:
        await require_capacity(session.jobs, job.owner_id, creating=False)
        payload = resumed_payload(job)
        refresh_summary(payload)
        # Includes MonthlyBudgetExhausted, an InvalidRequest, for the owner and subscription.
        await session.require_admission_room(job.owner_id, edition.subscription_id, now)
    except (InvalidRequest, RateLimited, JobInterrupted):
        # Keep the block and postpone the next probe by the same interval.
        postponed = replace(edition, updated_at=now, revision=edition.revision + 1)
        advanced = await session.editions.advance(postponed, expected_revision=edition.revision)
        await _commit_if(session, advanced is not None)
        return
    resumed = await session.jobs.resume(
        job.id, expected_revision=job.revision, now=now, payload=payload
    )
    if resumed is None:
        await session.rollback()
        return
    queued = replace(
        edition,
        workflow=EditionWorkflow.QUEUED,
        safe_reason=None,
        updated_at=now,
        revision=edition.revision + 1,
    )
    advanced = await session.editions.advance(queued, expected_revision=edition.revision)
    await _commit_if(session, advanced is not None)
