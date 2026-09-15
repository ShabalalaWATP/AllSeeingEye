"""Atomic schedule activation and checkpoint-safe control of its active edition."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.application.dto import RequestContext
from ase.application.report_jobs.controls import require_capacity, resumed_payload
from ase.application.report_jobs.views import refresh_summary
from ase.application.schedules.manage import SetScheduleEnabledUseCase
from ase.domain.errors import Conflict
from ase.domain.schedules import Schedule
from ase.domain.subscription_editions import EditionWorkflow, SubscriptionEdition

if TYPE_CHECKING:
    from ase.container import Container
    from ase.domain.users import User


async def _pause_active(
    container: Container,
    session: AsyncSession,
    edition: SubscriptionEdition | None,
) -> tuple[UUID, UUID | None] | None:
    if (
        edition is None
        or edition.job_id is None
        or edition.workflow not in {EditionWorkflow.QUEUED, EditionWorkflow.RUNNING}
    ):
        return None
    jobs = SqlReportJobRepository(session)
    job = await jobs.get(edition.job_id)
    if job is None:
        raise Conflict("The active subscription job is unavailable.")
    if job.status not in {"queued", "running", "paused"}:
        return None  # Publication may already have won its completion race.
    if job.status in {"queued", "running"}:
        paused = await jobs.pause(job.id, expected_revision=job.revision, now=container.clock.now())
        if paused is None:
            raise Conflict("The active subscription job changed during pause.")
    ledger = SqlSubscriptionEditionRepository(session)
    staged = await ledger.advance(
        replace(
            edition,
            workflow=EditionWorkflow.PAUSED,
            safe_reason="schedule_paused",
            updated_at=container.clock.now(),
            revision=edition.revision + 1,
        ),
        expected_revision=edition.revision,
    )
    if staged is None:
        raise Conflict("The active subscription edition changed during pause.")
    return job.id, job.lease_token


async def _cancel_archived_active(
    container: Container, session: AsyncSession, edition: SubscriptionEdition | None
) -> tuple[UUID, UUID | None] | None:
    if edition is None:
        return None
    cancellation = None
    if edition.job_id is not None:
        jobs = SqlReportJobRepository(session)
        job = await jobs.get(edition.job_id)
        if job is None:
            raise Conflict("The active subscription job is unavailable.")
        if job.status in {"queued", "running"}:
            paused = await jobs.pause(
                job.id, expected_revision=job.revision, now=container.clock.now()
            )
            if paused is None:
                raise Conflict("The active subscription job changed during archive.")
            cancellation = job.id, job.lease_token
    ledger = SqlSubscriptionEditionRepository(session)
    cancelled = await ledger.advance(
        replace(
            edition,
            workflow=EditionWorkflow.CANCELLED,
            safe_reason="subscription_archived",
            updated_at=container.clock.now(),
            revision=edition.revision + 1,
        ),
        expected_revision=edition.revision,
    )
    if cancelled is None:
        raise Conflict("The active subscription edition changed during archive.")
    return cancellation


async def _resume_active(
    container: Container, session: AsyncSession, edition: SubscriptionEdition | None
) -> None:
    if (
        edition is None
        or edition.job_id is None
        or edition.workflow is not EditionWorkflow.PAUSED
        or edition.safe_reason != "schedule_paused"
    ):
        return
    jobs = SqlReportJobRepository(session)
    job = await jobs.get(edition.job_id)
    if job is None or job.status != "paused":
        raise Conflict("The retained subscription job changed during resume.")
    await container.report_job_gate(session, job)
    await require_capacity(jobs, job.owner_id, creating=False)
    payload = resumed_payload(job)
    refresh_summary(payload)
    resumed = await jobs.resume(
        job.id, expected_revision=job.revision, now=container.clock.now(), payload=payload
    )
    if resumed is None:
        raise Conflict("The retained subscription job changed during resume.")
    ledger = SqlSubscriptionEditionRepository(session)
    staged = await ledger.advance(
        replace(
            edition,
            workflow=EditionWorkflow.QUEUED,
            safe_reason=None,
            updated_at=container.clock.now(),
            revision=edition.revision + 1,
        ),
        expected_revision=edition.revision,
    )
    if staged is None:
        raise Conflict("The active subscription edition changed during resume.")


async def control_schedule(
    container: Container,
    session: AsyncSession,
    actor: User,
    schedule_id: UUID,
    enabled: bool,
    context: RequestContext,
    *,
    check_session: Callable[[], Awaitable[None]],
) -> Schedule:
    """The source guard serialises admission with activation; the DB owns durability."""
    await check_session()
    cancellation: tuple[UUID, UUID | None] | None = None
    async with container.source_admission.guard():
        try:
            repos = container.repositories(session)
            schedule, changed = await SetScheduleEnabledUseCase(
                repos.schedules,
                container.access_policy(session),
                container._auditor(repos),
                container.clock,
            ).stage(actor, schedule_id, enabled, context)
            edition = await SqlSubscriptionEditionRepository(session).active(schedule_id)
            if not enabled:
                cancellation = await _pause_active(container, session, edition)
            elif changed:
                await _resume_active(container, session, edition)
            await check_session()
            await repos.uow.commit()
        except BaseException:
            await session.rollback()
            raise
        if cancellation is not None:
            container.report_job_worker.cancel(*cancellation)
    return schedule


async def archive_schedule(
    container: Container,
    session: AsyncSession,
    actor: User,
    schedule_id: UUID,
    context: RequestContext,
    *,
    check_session: Callable[[], Awaitable[None]],
) -> None:
    """Tombstone and pause active work under the admission guard in one commit."""
    await check_session()
    cancellation: tuple[UUID, UUID | None] | None = None
    async with container.source_admission.guard():
        try:
            _, changed = await container.delete_schedule(session).stage(actor, schedule_id, context)
            if changed:
                edition = await SqlSubscriptionEditionRepository(session).active(schedule_id)
                cancellation = await _cancel_archived_active(container, session, edition)
            await check_session()
            await container.repositories(session).uow.commit()
        except BaseException:
            await session.rollback()
            raise
        if cancellation is not None:
            container.report_job_worker.cancel(*cancellation)
