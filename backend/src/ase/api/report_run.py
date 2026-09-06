"""Request-bound report generation with local progress and cooperative cancellation."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Protocol
from uuid import UUID

from fastapi import HTTPException, Request

from ase.application.reports.progress import Progress
from ase.domain.errors import NotFound
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.research_runs import ResearchRun, ResearchStage
from ase.domain.users import User

GENERATION_TIMEOUT_SECONDS = 600.0
GenerationResult = tuple[ReportRecord, ReportVersion]


class RunStore(Protocol):
    def reserve(self, actor: User, run_id: UUID) -> ResearchRun: ...
    def update(
        self, actor: User, run_id: UUID, stage: ResearchStage, report_id: UUID | None = None
    ) -> ResearchRun: ...


class _Interrupted(HTTPException):
    def __init__(self, stage: ResearchStage) -> None:
        self.stage = stage
        super().__init__(
            status_code=504 if stage is ResearchStage.TIMED_OUT else 499,
            detail="Report generation timed out."
            if stage is ResearchStage.TIMED_OUT
            else "The report request was disconnected.",
        )
        self.detail += " If saving had started, check Reports before retrying."


async def _disconnect(request: Request) -> None:
    # Routes have already parsed their bodies. Await the ASGI channel directly:
    # is_disconnected() introduces a cancelled AnyIO scope which can consume this
    # watcher's cancellation and leave response cleanup waiting indefinitely.
    while (await request.receive())["type"] != "http.disconnect":
        pass


async def _result(
    work: asyncio.Task[GenerationResult], watcher: asyncio.Task[None]
) -> GenerationResult:
    done, _ = await asyncio.wait(
        (work, watcher), timeout=GENERATION_TIMEOUT_SECONDS, return_when=asyncio.FIRST_COMPLETED
    )
    if work in done:
        return work.result()
    stage = ResearchStage.CANCELLED if watcher in done else ResearchStage.TIMED_OUT
    if watcher in done:
        watcher.result()  # A transport failure must not leave detached report work running.
    work.cancel()
    try:
        # A completed commit can win the cancellation race. Preserve its actual result.
        return await work
    except asyncio.CancelledError:
        raise _Interrupted(stage) from None


async def run_generation(
    request: Request,
    actor: User,
    runs: RunStore,
    run_id: UUID | None,
    operation: Callable[[Progress], Awaitable[GenerationResult]],
    *,
    before_save: Callable[[], Awaitable[None]] | None = None,
) -> GenerationResult:
    """Keep work in this request/session; cancellation propagates into model and feed calls.

    The caller's session dependency rolls back unfinished writes on close. A connection
    lost during commit has an indeterminate outcome, so cancellation is not a deletion
    guarantee. No raw source text, model output or query is stored in progress records.
    """
    if run_id is not None:
        runs.reserve(actor, run_id)

    def update(stage: ResearchStage, report_id: UUID | None = None) -> None:
        if run_id is not None:
            # An expired ephemeral receipt must not abort an otherwise valid report.
            with suppress(NotFound):
                runs.update(actor, run_id, stage, report_id)

    async def progress(stage: ResearchStage) -> None:
        if stage is ResearchStage.SAVING and before_save is not None:
            await before_save()
        update(stage)

    async def invoke() -> GenerationResult:
        return await operation(progress)

    work = asyncio.create_task(invoke())
    watcher = asyncio.create_task(_disconnect(request))
    try:
        result = await _result(work, watcher)
        update(ResearchStage.COMPLETED, result[0].id)
        return result
    except _Interrupted as exc:
        update(exc.stage)
        raise
    except asyncio.CancelledError:
        work.cancel()
        await asyncio.gather(work, return_exceptions=True)
        update(ResearchStage.CANCELLED)
        raise
    except Exception:
        work.cancel()
        await asyncio.gather(work, return_exceptions=True)
        update(ResearchStage.FAILED)
        raise
    finally:
        watcher.cancel()
        await asyncio.gather(watcher, return_exceptions=True)
