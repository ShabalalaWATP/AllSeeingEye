"""Cleanup timing includes failures and preserves dependency ordering."""

import asyncio
from contextlib import AsyncExitStack

import pytest
from structlog.testing import capture_logs

from ase.infrastructure.shutdown import ShutdownPhases


async def test_shutdown_phases_log_dependency_order_and_elapsed_time():
    phases = ShutdownPhases()

    async def stop():
        await asyncio.sleep(0.001)

    with capture_logs() as logs:
        async with AsyncExitStack() as cleanup:
            for name in ("dispose", "live_snapshot", "scheduler", "report_jobs", "admission"):
                cleanup.push_async_callback(phases.run, name, stop)
        phases.complete()
    assert [item["phase"] for item in logs[:-1]] == [
        "admission",
        "report_jobs",
        "scheduler",
        "live_snapshot",
        "dispose",
    ]
    assert all(item["duration_ms"] > 0 for item in logs)
    assert logs[-1]["event"] == "shutdown.complete"
    assert logs[-1]["outcome"] == "completed"


async def test_timeout_still_attempts_later_cleanup_and_logs_failed_completion():
    phases = ShutdownPhases(budget=0.02)
    disposed = []

    async def blocked():
        await asyncio.Event().wait()

    async def dispose():
        disposed.append(True)

    with capture_logs() as logs, pytest.raises(TimeoutError):
        try:
            async with AsyncExitStack() as cleanup:
                cleanup.push_async_callback(phases.run, "dispose", dispose)
                cleanup.push_async_callback(phases.run, "blocked", blocked)
        finally:
            phases.complete()
    assert disposed == [True]
    assert logs[0]["outcome"] == "timed_out"
    assert logs[-1]["outcome"] == "failed"
