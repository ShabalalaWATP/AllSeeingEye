"""Subscription worker retry transitions and retained attempt reconciliation."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Literal

from ase.application.ports import Clock
from ase.application.ports.subscription_admission import SourceGuard
from ase.application.ports.subscription_retry import (
    SubscriptionRetrySession,
    SubscriptionRetryTransactions,
)
from ase.application.report_jobs.budget import JobInterrupted
from ase.application.report_jobs.controls import has_budget
from ase.application.report_jobs.recovery import SECTION_FAILURES
from ase.application.report_jobs.views import refresh_summary
from ase.application.schedules.subscription_retry_runtime import (
    automatic_retry_payload,
    classify_failure,
)
from ase.domain.errors import RateLimited
from ase.domain.report_jobs import ReportJob
from ase.domain.subscription_editions import EditionWorkflow
from ase.domain.subscription_monthly_budget import MonthlyBudgetExhausted
from ase.domain.subscription_retry import RETRY_HORIZON, RetryAction, RetryContext, decide_retry


class SubscriptionRetry:
    def __init__(
        self, transactions: SubscriptionRetryTransactions, clock: Clock, guard: SourceGuard
    ) -> None:
        self.transactions, self.clock, self.guard = transactions, clock, guard

    async def pause(self, stored: ReportJob, code: str, error: BaseException | None = None) -> None:
        async with self.transactions() as session:
            repo = session.jobs
            editions = session.editions
            current = await repo.get(stored.id)
            if (
                current is None
                or current.status != "running"
                or current.lease_token is None
                or current.lease_token != stored.lease_token
            ):
                return
            now = self.clock.now()
            edition = await editions.get_by_job(stored.id)
            attempt = await session.latest_attempt(edition.id) if edition is not None else None
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
                    first = await session.first_failure_at(edition.id) or now
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
                if attempt is not None and not await session.finish_attempt(
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
        async with self.transactions() as session:
            editions = session.editions
            edition = await editions.get_by_job(stored.id)
            current = await session.jobs.get(stored.id)
            if (
                edition is None
                or current is None
                or stored.lease_token is None
                or current.status not in {"completed", "needs_review"}
            ):
                return
            if await session.finish_attempt(
                edition.id,
                current,
                stored.lease_token,
                self.clock.now(),
                "completed",
            ):
                await session.commit()

    async def recover_expired_editions(
        self, session: SubscriptionRetrySession, now: datetime
    ) -> None:
        editions = session.editions
        rows = await session.recoverable_editions()
        for edition_id in rows:
            edition = await editions.get(edition_id)
            if (
                edition is None
                or edition.job_id is None
                or edition.workflow is not EditionWorkflow.RUNNING
            ):
                continue
            job = await session.jobs.get(edition.job_id)
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
            attempt = await session.latest_attempt(edition.id)
            if (
                attempt is not None
                and attempt.ended_at is None
                and attempt.lease_token is not None
                and not await session.finish_attempt(
                    edition.id, job, attempt.lease_token, now, reason
                )
            ):
                await session.rollback()

    async def resume_due(self) -> None:  # noqa: PLR0912, PLR0915 - fenced state machine
        now = self.clock.now()
        async with self.transactions() as session:
            due = await session.due_retry_ids(now)
        for edition_id in due:
            async with (
                self.guard(),
                self.transactions() as session,
            ):
                # Match schedule controls: source guard, then the DB administration guard.
                await session.lock_administration()
                editions = session.editions
                jobs = session.jobs
                edition = await editions.get(edition_id)
                if (
                    edition is None
                    or edition.workflow is not EditionWorkflow.RETRY_WAIT
                    or edition.job_id is None
                ):
                    continue
                schedule = await session.schedules.get(edition.subscription_id)
                if schedule is None or not schedule.enabled or schedule.archived_at is not None:
                    continue
                job = await jobs.get(edition.job_id)
                attempt = await session.latest_attempt(edition_id)
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
                first = await session.first_failure_at(edition.id)
                if first is None:
                    await session.rollback()
                    continue
                if first.tzinfo is None:
                    first = first.replace(tzinfo=UTC)
                if now >= first + RETRY_HORIZON:
                    if await session.stop_waiting(
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
                    if await session.stop_waiting(
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
                    if await session.stop_waiting(
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
                    await session.require_admission_room(
                        job.owner_id,
                        edition.subscription_id,
                        now,
                    )
                except MonthlyBudgetExhausted:
                    if await session.stop_waiting(
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
