"""Own worker startup and unwind resources even after partial startup failure."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from time import perf_counter
from typing import Protocol

from fastapi import FastAPI

from ase.application.worker_progress import worker_heartbeats
from ase.container import Container
from ase.container.alert_routing import alert_dispatcher
from ase.container.annotation_monitor_worker import build_annotation_monitor_worker
from ase.container.live_snapshot import build_live_snapshot
from ase.container.notifications import digest_worker, notification_dispatcher
from ase.container.original_asset_expiry import expire_original_assets
from ase.container.runtime_health import RuntimeHealth
from ase.container.web_push import run_web_push
from ase.infrastructure.shutdown import ShutdownPhases
from ase.infrastructure.startup import record_startup_phase


class _Worker(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...


async def _start(
    cleanup: AsyncExitStack, worker: _Worker, phases: ShutdownPhases, name: str
) -> None:
    # start() may create tasks before failing, so own stop() before entering it.
    cleanup.push_async_callback(phases.run, name, worker.stop)
    await worker.start()


async def _cancel(task: asyncio.Task[None]) -> None:
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    startup_started = perf_counter()
    container: Container = app.state.container
    runtime: RuntimeHealth = getattr(app.state, "runtime", None) or RuntimeHealth()
    app.state.runtime = runtime
    phases = ShutdownPhases()
    binding = worker_heartbeats.set(runtime.workers)
    try:
        async with AsyncExitStack() as cleanup:
            # Register first so clients/database remain available until workers stop.
            # AsyncExitStack runs every callback and retains errors through chaining.
            cleanup.push_async_callback(phases.run, "dispose", container.dispose)
            cleanup.push_async_callback(phases.run, "runtime_monitor", runtime.stop)
            runtime.start()
            # Restore retained public events before any feed starts. Its final save
            # runs after every worker below has stopped (ADR 0022).
            snapshot_started = perf_counter()
            snapshot = build_live_snapshot(container)
            if snapshot is not None:
                await _start(cleanup, snapshot, phases, "live_snapshot")
            record_startup_phase("snapshot_restore", snapshot_started)
            workers_started = perf_counter()
            if container.settings.feeds_enabled:
                await _start(cleanup, container.scheduler, phases, "scheduler")
                await _start(cleanup, container.aviation_monitor, phases, "aviation_monitor")
                await _start(cleanup, container.evaluator, phases, "evaluator")
                await _start(cleanup, container.translation_queue, phases, "translation_queue")
                await _start(cleanup, container.conflict_screening, phases, "conflict_screening")
                await _start(cleanup, container.social_monitor, phases, "social_monitor")
            # Stop admission before consumers, then housekeeping, then feed workers.
            # Separate stacks retain this dependency order even on partial startup.
            housekeeping = await cleanup.enter_async_context(AsyncExitStack())
            reporting = await cleanup.enter_async_context(AsyncExitStack())
            admission = await cleanup.enter_async_context(AsyncExitStack())
            await _start(admission, container.schedule_runner, phases, "schedule_runner")
            asset_expiry = asyncio.create_task(
                expire_original_assets(container.session_factory, container.clock)
            )
            housekeeping.push_async_callback(
                phases.run, "asset_expiry", lambda: _cancel(asset_expiry)
            )
            annotation_monitoring = asyncio.create_task(
                build_annotation_monitor_worker(container).run()
            )
            housekeeping.push_async_callback(
                phases.run, "annotation_monitoring", lambda: _cancel(annotation_monitoring)
            )
            routed_alerts = asyncio.create_task(alert_dispatcher(container).run())
            housekeeping.push_async_callback(
                phases.run, "alert_notifications", lambda: _cancel(routed_alerts)
            )
            notifications = asyncio.create_task(notification_dispatcher(container).run())
            housekeeping.push_async_callback(
                phases.run, "edition_notifications", lambda: _cancel(notifications)
            )
            digests = asyncio.create_task(digest_worker(container).run())
            housekeeping.push_async_callback(
                phases.run, "digest_notifications", lambda: _cancel(digests)
            )
            browser_push = asyncio.create_task(run_web_push(container))
            housekeeping.push_async_callback(
                phases.run, "browser_push", lambda: _cancel(browser_push)
            )
            await _start(reporting, container.report_job_worker, phases, "report_job_worker")
            record_startup_phase("workers_started", workers_started)
            record_startup_phase("ready", startup_started)
            yield
    finally:
        worker_heartbeats.reset(binding)
        phases.complete()
