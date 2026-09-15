"""Bounded local workers, durable queue leases and explicit interruption recovery."""

import asyncio
from contextlib import suppress
from dataclasses import replace
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import structlog

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.subscription_editions import SqlSubscriptionEditionRepository
from ase.adapters.persistence.subscription_retry_attempts import (
    reconcile_stopped_attempts,
    start_attempt,
)
from ase.application.report_jobs.budget import JobBudgetExhausted, JobInterrupted
from ase.application.reports.sections import SectionIncomplete
from ase.container.report_job_checkpoints import ReportJobCheckpoints
from ase.container.report_job_execution import already_published, execute_job
from ase.container.report_job_gate import ReportJobChanged, ReportJobSourceDisabled
from ase.container.subscription_retry_orchestration import SubscriptionRetryOrchestrator
from ase.domain.errors import Forbidden, NoModelAvailable, NotFound, Unauthenticated
from ase.domain.report_jobs import ReportJob
from ase.domain.subscription_editions import EditionWorkflow
from ase.domain.subscription_monthly_budget import MonthlyBudgetExhausted

if TYPE_CHECKING:
    from ase.container import Container

log = structlog.get_logger(__name__)
CONCURRENCY = 2
LEASE_SECONDS = 45
MAX_RUN_SECONDS = 1800


def failure_code(error: BaseException) -> str:
    if isinstance(error, SectionIncomplete):
        return "section_" + error.reason
    mappings: tuple[tuple[tuple[type[BaseException], ...], str], ...] = (
        ((JobBudgetExhausted,), "budget_exhausted"),
        ((MonthlyBudgetExhausted,), "monthly_budget_exhausted"),
        ((ReportJobChanged, NoModelAvailable), "model_changed"),
        ((ReportJobSourceDisabled,), "source_disabled"),
        ((Unauthenticated, Forbidden, NotFound), "access_changed"),
        ((asyncio.CancelledError, JobInterrupted), "interrupted"),
        ((TimeoutError,), "time_limit"),
        ((ValueError,), "invalid_snapshot"),
    )
    return next((code for types, code in mappings if isinstance(error, types)), "provider_error")


class ReportJobWorker:
    def __init__(self, container: "Container") -> None:
        self.container = container
        self._retry = SubscriptionRetryOrchestrator(container)
        self._running: dict[UUID, tuple[UUID, asyncio.Task[None]]] = {}
        self._loop: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._loop is None:
            self._loop = asyncio.create_task(self.run())

    def cancel(self, job_id: UUID, lease_token: UUID | None) -> None:
        active = self._running.get(job_id)
        if active is not None and active[0] == lease_token:
            active[1].cancel()

    async def stop(self) -> None:
        if self._loop is not None:
            self._loop.cancel()
            await asyncio.gather(self._loop, return_exceptions=True)
            self._loop = None
        tasks = [task for _, task in self._running.values()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._running.clear()

    async def run(self) -> None:
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                # No provider exception, question or credentials enter operational logs.
                log.warning("report_jobs.queue_unavailable")
                await asyncio.sleep(10)
            await asyncio.sleep(2)

    async def tick(self) -> None:
        for key, (_, task) in tuple(self._running.items()):
            if task.done():
                with suppress(asyncio.CancelledError):
                    task.exception()
                self._running.pop(key, None)
        async with self.container.session_factory() as session:
            repo = SqlReportJobRepository(session)
            now = self.container.clock.now()
            await repo.recover_expired(now)
            await self._retry.recover_expired_editions(session, now)
            await reconcile_stopped_attempts(session, now)
            await session.commit()
        await self._retry.resume_due()
        async with self.container.session_factory() as session:
            repo = SqlReportJobRepository(session)
            available = await repo.queued(limit=CONCURRENCY)
        for key in available:
            if len(self._running) >= CONCURRENCY:
                break
            if key in self._running:
                continue
            async with self.container.session_factory() as session:
                repo = SqlReportJobRepository(session)
                editions = SqlSubscriptionEditionRepository(session)
                stored = await repo.get(key)
                if stored is None or stored.status != "queued":
                    continue
                edition = await editions.get_by_job(key)
                if edition is not None and edition.workflow is not EditionWorkflow.QUEUED:
                    continue
                token, now = uuid4(), self.container.clock.now()
                claimed = await repo.claim(
                    key,
                    expected_revision=stored.revision,
                    lease_token=token,
                    now=now,
                    lease_until=now + timedelta(seconds=LEASE_SECONDS),
                )
                if claimed is not None and edition is not None:
                    advanced = await editions.advance(
                        replace(
                            edition,
                            workflow=EditionWorkflow.RUNNING,
                            updated_at=now,
                            revision=edition.revision + 1,
                        ),
                        expected_revision=edition.revision,
                    )
                    if advanced is None:
                        await session.rollback()
                        continue
                    await start_attempt(session, edition, claimed, now)
                await session.commit()
            if claimed is not None:
                self._running[key] = (token, asyncio.create_task(self.process(claimed)))

    async def process(self, stored: ReportJob) -> None:
        if stored.lease_token is None:
            raise JobInterrupted()
        checkpoints = ReportJobCheckpoints(self.container, stored.id, stored.lease_token)
        work = asyncio.create_task(execute_job(self.container, stored, checkpoints))
        heartbeat = asyncio.create_task(self._heartbeat(checkpoints, work))
        try:
            async with asyncio.timeout(MAX_RUN_SECONDS):
                await work
        except BaseException as exc:
            work.cancel()
            await asyncio.gather(work, return_exceptions=True)
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            try:
                if await already_published(self.container, stored.id):
                    await self._retry.finish_published_attempt(stored)
                else:
                    await self._retry.pause(stored, failure_code(exc), exc)
            except Exception:
                # An expired lease is recovered as paused by the next queue pass.
                log.warning(
                    "report_jobs.interruption_checkpoint_unavailable", job_id=str(stored.id)
                )
        else:
            await self._retry.finish_published_attempt(stored)
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)

    async def _heartbeat(self, checkpoints: ReportJobCheckpoints, work: asyncio.Task[None]) -> None:
        try:
            while True:
                await asyncio.sleep(10)
                await checkpoints.mutate(lambda payload: None)
        except asyncio.CancelledError:
            raise
        except Exception:
            work.cancel()
