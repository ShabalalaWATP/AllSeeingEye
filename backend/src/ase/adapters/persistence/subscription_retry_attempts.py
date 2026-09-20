"""Durable attempt lifecycle and due retry lookup for subscription jobs."""

from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionAttemptRow,
    SubscriptionEditionRow,
)
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.report_jobs.budget import token_count
from ase.domain.report_jobs import ReportJob, job_error
from ase.domain.subscription_editions import EditionAttempt, SubscriptionEdition


async def latest_attempt(session: AsyncSession, edition_id: UUID) -> SubscriptionAttemptRow | None:
    return cast(
        SubscriptionAttemptRow | None,
        await session.scalar(
            select(SubscriptionAttemptRow)
            .where(SubscriptionAttemptRow.edition_id == edition_id)
            .order_by(SubscriptionAttemptRow.number.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        ),
    )


async def start_attempt(
    session: AsyncSession, edition: SubscriptionEdition, job: ReportJob, now: datetime
) -> EditionAttempt:
    previous = await latest_attempt(session, edition.id)
    # An explicit pause/resume may happen between worker ticks. Close the old
    # lease against the saved ledger before opening another attempt.
    if (
        previous is not None
        and previous.ended_at is None
        and (
            previous.lease_token is None
            or not await finish_attempt(
                session, edition.id, job, previous.lease_token, now, _stopped_outcome(job)
            )
        )
    ):
        raise ValueError("The previous edition attempt could not be reconciled.")
    attempt = EditionAttempt(
        id=uuid4(),
        edition_id=edition.id,
        job_id=job.id,
        number=previous.number + 1 if previous is not None else 1,
        stage=job.stage,
        started_at=now,
        ended_at=None,
        outcome="running",
        next_retry_at=None,
        lease_token=job.lease_token,
        job_revision=job.revision,
    )
    await SqlSubscriptionEditionRepository(session).add_attempt(attempt)
    return attempt


def _usage(calls: object, baseline: int) -> tuple[int, int, int, int]:
    if type(calls) is not list or baseline > len(calls):
        return 0, 0, 0, 0
    recent = calls[baseline:]
    if any(type(row) is not dict for row in recent):
        return 0, 0, 0, 0
    reserved = sum(token_count(row.get("reserved_output")) or 0 for row in recent)
    settled = [row for row in recent if row.get("status") in {"completed", "failed"}]
    actual = sum(token_count(row.get("completion_tokens")) or 0 for row in settled)
    return len(recent), len(settled), reserved, actual


async def finish_attempt(
    session: AsyncSession,
    edition_id: UUID,
    job: ReportJob,
    lease_token: UUID,
    now: datetime,
    outcome: str,
    next_retry_at: datetime | None = None,
) -> bool:
    job_error(outcome)
    attempt = await latest_attempt(session, edition_id)
    if (
        attempt is None
        or attempt.job_id != job.id
        or attempt.lease_token != lease_token
        or attempt.ended_at is not None
    ):
        return False
    baseline = await session.scalar(
        select(func.coalesce(func.sum(SubscriptionAttemptRow.reserved_requests), 0)).where(
            SubscriptionAttemptRow.edition_id == edition_id,
            SubscriptionAttemptRow.number < attempt.number,
        )
    )
    reserved_count, actual_count, reserved_tokens, actual_tokens = _usage(
        job.payload.get("calls", []), int(baseline or 0)
    )
    changed = await session.scalar(
        update(SubscriptionAttemptRow)
        .where(SubscriptionAttemptRow.id == attempt.id, SubscriptionAttemptRow.ended_at.is_(None))
        .values(
            stage=job.stage,
            ended_at=now,
            outcome=outcome,
            next_retry_at=next_retry_at,
            reserved_requests=reserved_count,
            actual_requests=actual_count,
            reserved_output_tokens=reserved_tokens,
            actual_output_tokens=actual_tokens,
        )
        .returning(SubscriptionAttemptRow.id)
        .execution_options(synchronize_session=False)
    )
    return changed is not None


def _stopped_outcome(job: ReportJob) -> str:
    if job.status in {"completed", "needs_review"}:
        return "completed"
    calls = job.payload.get("calls", [])
    if type(calls) is not list or any(
        type(row) is not dict or row.get("status") in {"in_flight", "uncertain"} for row in calls
    ):
        return "uncertain_paid_outcome"
    return job.error or "interrupted"


async def reconcile_stopped_attempts(session: AsyncSession, now: datetime, limit: int = 20) -> None:
    """Close attempts stopped by explicit controls or publication before this tick."""
    rows = await session.scalars(
        select(SubscriptionAttemptRow.edition_id)
        .join(ReportJobRow, SubscriptionAttemptRow.job_id == ReportJobRow.id)
        .join(
            SubscriptionEditionRow, SubscriptionAttemptRow.edition_id == SubscriptionEditionRow.id
        )
        .where(
            SubscriptionAttemptRow.ended_at.is_(None),
            ReportJobRow.status.in_(("paused", "failed", "completed", "needs_review")),
            SubscriptionEditionRow.workflow != "running",
        )
        .order_by(SubscriptionAttemptRow.started_at, SubscriptionAttemptRow.id)
        .limit(limit)
    )
    jobs = SqlReportJobRepository(session)
    for edition_id in rows:
        attempt = await latest_attempt(session, edition_id)
        if attempt is None or attempt.ended_at is not None or attempt.lease_token is None:
            continue
        job = await jobs.get(attempt.job_id) if attempt.job_id is not None else None
        if job is not None:
            await finish_attempt(
                session, edition_id, job, attempt.lease_token, now, _stopped_outcome(job)
            )


async def first_failure_at(session: AsyncSession, edition_id: UUID) -> datetime | None:
    return await session.scalar(
        select(func.min(SubscriptionAttemptRow.ended_at)).where(
            SubscriptionAttemptRow.edition_id == edition_id,
            SubscriptionAttemptRow.ended_at.is_not(None),
            SubscriptionAttemptRow.outcome == "known_transient_failure",
        )
    )


async def due_retry_ids(session: AsyncSession, now: datetime, limit: int = 20) -> list[UUID]:
    latest = (
        select(
            SubscriptionAttemptRow.edition_id,
            func.max(SubscriptionAttemptRow.number).label("number"),
        )
        .group_by(SubscriptionAttemptRow.edition_id)
        .subquery()
    )
    rows = await session.scalars(
        select(SubscriptionEditionRow.id)
        .join(latest, SubscriptionEditionRow.id == latest.c.edition_id)
        .join(ScheduleRow, SubscriptionEditionRow.subscription_id == ScheduleRow.id)
        .join(
            SubscriptionAttemptRow,
            and_(
                SubscriptionAttemptRow.edition_id == latest.c.edition_id,
                SubscriptionAttemptRow.number == latest.c.number,
            ),
        )
        .where(
            ScheduleRow.enabled.is_(True),
            ScheduleRow.archived_at.is_(None),
            SubscriptionEditionRow.workflow == "retry_wait",
            SubscriptionAttemptRow.outcome == "known_transient_failure",
            SubscriptionAttemptRow.next_retry_at <= now,
        )
        .order_by(SubscriptionAttemptRow.next_retry_at, SubscriptionEditionRow.id)
        .limit(limit)
    )
    return list(rows)
