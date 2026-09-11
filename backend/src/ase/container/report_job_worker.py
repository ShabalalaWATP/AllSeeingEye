"""Bounded local workers, durable queue leases and explicit interruption recovery."""

import asyncio
from contextlib import suppress
from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import structlog

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.report_jobs.budget import JobBudgetExhausted, JobInterrupted
from ase.application.reports.sections import SectionIncomplete
from ase.container.report_job_checkpoints import ReportJobCheckpoints
from ase.container.report_job_execution import already_published, execute_job
from ase.container.report_job_gate import ReportJobChanged, ReportJobSourceDisabled
from ase.domain.errors import Forbidden, NoModelAvailable, NotFound, Unauthenticated
from ase.domain.report_jobs import ReportJob

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
            await repo.recover_expired(self.container.clock.now())
            await session.commit()
            available = await repo.queued(limit=CONCURRENCY)
        for key in available:
            if len(self._running) >= CONCURRENCY:
                break
            if key in self._running:
                continue
            async with self.container.session_factory() as session:
                repo = SqlReportJobRepository(session)
                stored = await repo.get(key)
                if stored is None or stored.status != "queued":
                    continue
                token, now = uuid4(), self.container.clock.now()
                claimed = await repo.claim(
                    key,
                    expected_revision=stored.revision,
                    lease_token=token,
                    now=now,
                    lease_until=now + timedelta(seconds=LEASE_SECONDS),
                )
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
                if not await already_published(self.container, stored.id):
                    await self._pause(stored, failure_code(exc))
            except Exception:
                # An expired lease is recovered as paused by the next queue pass.
                log.warning(
                    "report_jobs.interruption_checkpoint_unavailable", job_id=str(stored.id)
                )
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

    async def _pause(self, stored: ReportJob, code: str) -> None:
        async with self.container.session_factory() as session:
            repo = SqlReportJobRepository(session)
            current = await repo.get(stored.id)
            if (
                current is None
                or current.status != "running"
                or current.lease_token is None
                or current.lease_token != stored.lease_token
            ):
                return
            await repo.checkpoint(
                current.id,
                expected_revision=current.revision,
                lease_token=current.lease_token,
                payload=current.payload,
                stage="paused",
                now=self.container.clock.now(),
                status="paused",
                error=code,
            )
            await session.commit()
