"""Own worker startup and unwind resources even after partial startup failure."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Protocol

from fastapi import FastAPI

from ase.container import Container
from ase.container.annotation_monitor_worker import build_annotation_monitor_worker
from ase.container.original_asset_expiry import expire_original_assets


class _Worker(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...


async def _start(cleanup: AsyncExitStack, worker: _Worker) -> None:
    # start() may create tasks before failing, so own stop() before entering it.
    cleanup.push_async_callback(worker.stop)
    await worker.start()


async def _cancel(task: asyncio.Task[None]) -> None:
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container: Container = app.state.container
    async with AsyncExitStack() as cleanup:
        # Register first so clients/database remain available until workers stop.
        # AsyncExitStack runs every callback and retains errors through chaining.
        cleanup.push_async_callback(container.dispose)
        if container.settings.feeds_enabled:
            await _start(cleanup, container.scheduler)
            await _start(cleanup, container.aviation_monitor)
            await _start(cleanup, container.evaluator)
            await _start(cleanup, container.translation_queue)
            await _start(cleanup, container.conflict_screening)
            await _start(cleanup, container.social_monitor)
        # Stop admission before consumers, then housekeeping, then feed workers.
        # Separate stacks retain this dependency order even on partial startup.
        housekeeping = await cleanup.enter_async_context(AsyncExitStack())
        reporting = await cleanup.enter_async_context(AsyncExitStack())
        admission = await cleanup.enter_async_context(AsyncExitStack())
        await _start(admission, container.schedule_runner)
        asset_expiry = asyncio.create_task(
            expire_original_assets(container.session_factory, container.clock)
        )
        housekeeping.push_async_callback(_cancel, asset_expiry)
        annotation_monitoring = asyncio.create_task(
            build_annotation_monitor_worker(container).run()
        )
        housekeeping.push_async_callback(_cancel, annotation_monitoring)
        await _start(reporting, container.report_job_worker)
        yield
