"""Subscription worker retry transitions and retained attempt reconciliation."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.monthly_report_usage import require_admission_room
from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_edition_models import SubscriptionEditionRow
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.adapters.persistence.subscription_retry_attempts import (
    due_retry_ids,
    finish_attempt,
    first_failure_at,
    latest_attempt,
)
from ase.application.report_jobs.budget import JobInterrupted
from ase.application.report_jobs.controls import has_budget
from ase.application.report_jobs.recovery import SECTION_FAILURES
from ase.application.report_jobs.views import refresh_summary
from ase.container.subscription_retry_runtime import automatic_retry_payload, classify_failure
from ase.container.subscription_retry_transitions import stop_waiting
from ase.domain.errors import RateLimited
from ase.domain.report_jobs import ReportJob
from ase.domain.subscription_editions import EditionWorkflow
from ase.domain.subscription_monthly_budget import MonthlyBudgetExhausted
from ase.domain.subscription_retry import RETRY_HORIZON, RetryAction, RetryContext, decide_retry

if TYPE_CHECKING:
    from ase.container import Container


class SubscriptionRetryOrchestrator:
    def __init__(self, container: Container) -> None:
        self.container = container

    async def pause(self, stored: ReportJob, code: str, error: BaseException | None = None) -> None:
        async with self.container.session_factory() as session:
            repo = SqlReportJobRepository(session)
            editions = SqlSubscriptionEditionRepository(session)
            current = await repo.get(stored.id)
            if (
                current is None
                or current.status != "running"
                or current.lease_token is None
                or current.lease_token != stored.lease_token
            ):
                return
            now = self.container.clock.now()
            edition = await editions.get_by_job(stored.id)
            attempt = await latest_attempt(session, edition.id) if edition is not None else None
            decision = None
            payload = current.payload
            if (
                edition is not None
                and attempt is not None
                and attempt.ended_at is None
                and attempt.lease_token == current.lease_token
                and error is not None
            ):
                failure = classify_failure(error, code, stored.payload, current.payload)
                if failure is not None:
                    first = await first_failure_at(session, edition.id) or now
                    if first.tzinfo is None:
                        first = first.replace(tzinfo=UTC)
                    try:
                        budget_available = has_budget(current.payload)
                    except (ValueError, JobInterrupted):
                        budget_available = False
                    decision = decide_retry(
                        RetryContext(
                            edition_id=edition.id,
                            failure=failure,
                            failed_attempt=attempt.number,
                            first_failed_at=first,
                            now=now,
                            retry_after=str(error.retry_after)
                            if isinstance(error, RateLimited)
                            else None,
                            budget_available=budget_available,
                        )
                    )
                    if decision.action is RetryAction.RETRY_WAIT:
                        safe = automatic_retry_payload(current.payload)
                        if safe is None:
                            decision = None
                        else:
                            payload = safe
                            refresh_summary(payload)
            reason = decision.reason if decision is not None else code
            job_status: Literal["paused", "failed"] = (
                "failed" if decision and decision.action is RetryAction.FAIL else "paused"
            )
            paused = await repo.checkpoint(
                current.id,
                expected_revision=current.revision,
                lease_token=current.lease_token,
                payload=payload,
                stage="failed" if job_status == "failed" else "paused",
                now=now,
                status=job_status,
                error=reason,
            )
            if paused is None:
                await session.rollback()
                return
            if edition is not None and edition.workflow is EditionWorkflow.RUNNING:
                workflow = (
                    {
                        RetryAction.RETRY_WAIT: EditionWorkflow.RETRY_WAIT,
                        RetryAction.BLOCK: EditionWorkflow.BLOCKED,
                        RetryAction.FAIL: EditionWorkflow.FAILED,
                    }.get(decision.action, EditionWorkflow.PAUSED)
                    if decision is not None
                    else EditionWorkflow.PAUSED
                )
                updated = await editions.advance(
                    replace(
                        edition,
                        workflow=workflow,
                        safe_reason=reason,
                        updated_at=now,
                        revision=edition.revision + 1,
                    ),
                    expected_revision=edition.revision,
                )
                if updated is None:
                    await session.rollback()
                    return
                if attempt is not None and not await finish_attempt(
                    session,
                    edition.id,
                    current,
                    current.lease_token,
                    now,
                    reason,
                    decision.next_retry_at if decision is not None else None,
                ):
                    await session.rollback()
                    return
            await session.commit()

    async def finish_published_attempt(self, stored: ReportJob) -> None:
        async with self.container.session_factory() as session:
            editions = SqlSubscriptionEditionRepository(session)
            edition = await editions.get_by_job(stored.id)
            current = await SqlReportJobRepository(session).get(stored.id)
            if (
                edition is None
                or current is None
                or stored.lease_token is None
                or current.status not in {"completed", "needs_review"}
            ):
                return
            if await finish_attempt(
                session,
                edition.id,
                current,
                stored.lease_token,
                self.container.clock.now(),
                "completed",
            ):
                await session.commit()

    async def recover_expired_editions(self, session: AsyncSession, now: datetime) -> None:
        editions = SqlSubscriptionEditionRepository(session)
        rows = await session.scalars(
            select(SubscriptionEditionRow.id)
            .join(ReportJobRow, SubscriptionEditionRow.job_id == ReportJobRow.id)
            .where(
                SubscriptionEditionRow.workflow == EditionWorkflow.RUNNING.value,
                ReportJobRow.status == "paused",
                ReportJobRow.error.in_({"interrupted_uncertain", *SECTION_FAILURES}),
            )
            .limit(20)
        )
        for edition_id in rows:
            edition = await editions.get(edition_id)
            if (
                edition is None
                or edition.job_id is None
                or edition.workflow is not EditionWorkflow.RUNNING
            ):
                continue
            job = await SqlReportJobRepository(session).get(edition.job_id)
            if (
                job is None
                or job.status != "paused"
                or job.error not in {"interrupted_uncertain", *SECTION_FAILURES}
            ):
                continue
            reason = job.error if job.error in SECTION_FAILURES else "uncertain_paid_outcome"
            changed = await editions.advance(
                replace(
                    edition,
                    workflow=EditionWorkflow.PAUSED,
                    safe_reason=reason,
                    updated_at=now,
                    revision=edition.revision + 1,
                ),
                expected_revision=edition.revision,
            )
            if changed is None:
                continue
            attempt = await latest_attempt(session, edition.id)
            if (
                attempt is not None
                and attempt.ended_at is None
                and attempt.lease_token is not None
                and not await finish_attempt(
                    session, edition.id, job, attempt.lease_token, now, reason
                )
            ):
                await session.rollback()

    async def resume_due(self) -> None:  # noqa: PLR0912, PLR0915 - fenced state machine
        now = self.container.clock.now()
        async with self.container.session_factory() as session:
            due = await due_retry_ids(session, now)
        for edition_id in due:
            async with (
                self.container.source_admission.guard(),
                self.container.session_factory() as session,
            ):
                # Match schedule controls: source guard, then the DB administration guard.
                repos = self.container.repositories(session)
                await repos.users.lock_administration()
                editions = SqlSubscriptionEditionRepository(session)
                jobs = SqlReportJobRepository(session)
                edition = await editions.get(edition_id)
                if (
                    edition is None
                    or edition.workflow is not EditionWorkflow.RETRY_WAIT
                    or edition.job_id is None
                ):
                    continue
                schedule = await repos.schedules.get(edition.subscription_id)
                if schedule is None or not schedule.enabled or schedule.archived_at is not None:
                    continue
                job = await jobs.get(edition.job_id)
                attempt = await latest_attempt(session, edition_id)
                if (
                    job is None
                    or job.status != "paused"
                    or job.error != "known_transient_failure"
                    or attempt is None
                    or attempt.outcome != "known_transient_failure"
                    or attempt.next_retry_at is None
                    or attempt.next_retry_at > now
                ):
                    continue
                first = await first_failure_at(session, edition.id)
                if first is None:
                    await session.rollback()
                    continue
                if first.tzinfo is None:
                    first = first.replace(tzinfo=UTC)
                if now >= first + RETRY_HORIZON:
                    if await stop_waiting(
                        session,
                        edition,
                        job,
                        EditionWorkflow.FAILED,
                        "retry_horizon_exhausted",
                        now,
                    ):
                        await session.commit()
                    else:
                        await session.rollback()
                    continue
                if automatic_retry_payload(job.payload) is None:
                    if await stop_waiting(
                        session,
                        edition,
                        job,
                        EditionWorkflow.PAUSED,
                        "retry_checkpoint_unavailable",
                        now,
                    ):
                        await session.commit()
                    else:
                        await session.rollback()
                    continue
                try:
                    affordable = has_budget(job.payload)
                except (ValueError, JobInterrupted):
                    affordable = False
                if not affordable:
                    if await stop_waiting(
                        session,
                        edition,
                        job,
                        EditionWorkflow.BLOCKED,
                        "budget_unavailable",
                        now,
                    ):
                        await session.commit()
                    else:
                        await session.rollback()
                    continue
                try:
                    await require_admission_room(
                        session,
                        job.owner_id,
                        edition.subscription_id,
                        now,
                        self.container.monthly_budget_policy,
                    )
                except MonthlyBudgetExhausted:
                    if await stop_waiting(
                        session,
                        edition,
                        job,
                        EditionWorkflow.BLOCKED,
                        "monthly_budget_exhausted",
                        now,
                    ):
                        await session.commit()
                    else:
                        await session.rollback()
                    continue
                resumed = await jobs.resume(job.id, expected_revision=job.revision, now=now)
                if resumed is None:
                    await session.rollback()
                    continue
                advanced = await editions.advance(
                    replace(
                        edition,
                        workflow=EditionWorkflow.QUEUED,
                        safe_reason=None,
                        updated_at=now,
                        revision=edition.revision + 1,
                    ),
                    expected_revision=edition.revision,
                )
                if advanced is None:
                    await session.rollback()
                    continue
                await session.commit()
