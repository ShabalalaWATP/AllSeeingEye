"""Ownership survives partial startup and failures during shutdown."""

import asyncio
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI

from ase.app_lifecycle import lifespan
from ase.application.ukraine_digest import UkraineDigestService
from ase.container.economy import EconomyWiring
from ase.container.lifecycle import dispose_resources

WORKERS = (
    "scheduler",
    "aviation_monitor",
    "evaluator",
    "translation_queue",
    "conflict_screening",
    "social_monitor",
    "schedule_runner",
    "report_job_worker",
)


@pytest.fixture
def runtime(monkeypatch):
    tasks = []

    async def idle(*_args):
        tasks.append(asyncio.current_task())
        await asyncio.Event().wait()

    monkeypatch.setattr("ase.app_lifecycle.expire_original_assets", idle)
    monkeypatch.setattr(
        "ase.app_lifecycle.build_annotation_monitor_worker", lambda _: SimpleNamespace(run=idle)
    )
    container = SimpleNamespace(
        settings=SimpleNamespace(feeds_enabled=True),
        dispose=AsyncMock(),
        session_factory=Mock(),
        clock=Mock(),
        **{name: SimpleNamespace(start=AsyncMock(), stop=AsyncMock()) for name in WORKERS},
    )
    app = FastAPI()
    app.state.container = container
    return app, container, tasks


@pytest.mark.parametrize("failed", WORKERS)
async def test_partial_startup_stops_owned_workers_and_disposes(runtime, failed):
    app, container, tasks = runtime
    original = RuntimeError("startup failed")
    getattr(container, failed).start.side_effect = original
    with pytest.raises(RuntimeError) as caught:
        async with lifespan(app):
            pytest.fail("Startup must not yield")
    assert caught.value is original
    for name in WORKERS[: WORKERS.index(failed) + 1]:
        getattr(container, name).stop.assert_awaited_once()
    container.dispose.assert_awaited_once()
    assert all(task.done() for task in tasks)


@pytest.mark.parametrize("failed", WORKERS)
async def test_cleanup_continues_and_retains_original_failure(runtime, failed):
    app, container, tasks = runtime
    original = RuntimeError("application failed")
    cleanup_failure = RuntimeError("shutdown failed")
    getattr(container, failed).stop.side_effect = cleanup_failure
    with pytest.raises(RuntimeError) as caught:
        async with lifespan(app):
            await asyncio.sleep(0)
            raise original
    assert caught.value is cleanup_failure
    assert caught.value.__context__ is original
    for name in WORKERS:
        getattr(container, name).stop.assert_awaited_once()
    container.dispose.assert_awaited_once()
    assert all(task.done() for task in tasks)


async def test_task_factory_failure_cancels_previously_created_task(runtime, monkeypatch):
    app, container, tasks = runtime
    monkeypatch.setattr(
        "ase.app_lifecycle.build_annotation_monitor_worker",
        Mock(side_effect=RuntimeError("task factory failed")),
    )
    with pytest.raises(RuntimeError, match="task factory failed"):
        async with lifespan(app):
            pytest.fail("Startup must not yield")
    for name in WORKERS[:-1]:
        getattr(container, name).stop.assert_awaited_once()
    container.dispose.assert_awaited_once()
    assert all(task.done() for task in tasks)


async def test_startup_cancellation_still_disposes_owned_resources(runtime):
    app, container, _ = runtime
    container.evaluator.start.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        async with lifespan(app):
            pytest.fail("Cancelled startup must not yield")
    for name in WORKERS[:3]:
        getattr(container, name).stop.assert_awaited_once()
    container.dispose.assert_awaited_once()


async def test_shutdown_stops_admission_before_consumers_and_clients(runtime):
    app, container, _ = runtime
    order = []
    for name in WORKERS:
        getattr(container, name).stop.side_effect = lambda name=name: order.append(name)
    container.dispose.side_effect = lambda: order.append("dispose")
    async with lifespan(app):
        pass
    assert order.index("schedule_runner") < order.index("report_job_worker")
    assert order.index("report_job_worker") < order.index("scheduler")
    assert order[-1] == "dispose"


def disposable_container():
    clients = (
        "http",
        "satellite_http",
        "marine_http",
        "barentswatch_http",
        "acled_tokens",
        "camera_http",
        "public_firms_http",
        "routing_http",
        "terrain_gateway",
        "terrain_http",
        "_llm_gateway",
        "_embedding_gateway",
        "tiles",
        "archiver",
    )
    return SimpleNamespace(
        **{name: SimpleNamespace(aclose=AsyncMock()) for name in clients},
        close_economy=AsyncMock(),
        close_web_search=AsyncMock(),
        engine=SimpleNamespace(dispose=AsyncMock()),
        ukraine_digest=SimpleNamespace(cancel=Mock(), drain=AsyncMock()),
    )


async def test_disposal_attempts_every_close_when_one_fails():
    container = disposable_container()
    container.close_economy.side_effect = RuntimeError("economy failed")
    with pytest.raises(RuntimeError, match="economy failed"):
        await dispose_resources(container)
    container.ukraine_digest.cancel.assert_called_once()
    for value in vars(container).values():
        if isinstance(value, SimpleNamespace) and hasattr(value, "aclose"):
            value.aclose.assert_awaited_once()
    container.close_web_search.assert_awaited_once()
    container.engine.dispose.assert_awaited_once()


async def test_digest_task_finalises_before_http_clients_and_database_close():
    container = disposable_container()
    digest = UkraineDigestService(
        Mock(), Mock(), Mock(), Mock(), Mock(), Mock(), Mock(), AsyncMock()
    )
    container.ukraine_digest = digest
    finalised = asyncio.Event()

    async def generate():
        try:
            await asyncio.Event().wait()
        finally:
            await asyncio.sleep(0)
            finalised.set()

    async def close_dependency():
        assert finalised.is_set(), "Digest task must finish before its dependencies close"
        assert digest._task.done()

    digest._task = asyncio.create_task(generate())
    await asyncio.sleep(0)
    container.http.aclose.side_effect = close_dependency
    container.engine.dispose.side_effect = close_dependency
    try:
        await dispose_resources(container)
        assert digest._task.cancelled()
    finally:
        digest.cancel()
        await digest.drain()


async def test_economy_failure_still_closes_its_owned_http_client():
    wiring = EconomyWiring()
    wiring.economy = SimpleNamespace(aclose=AsyncMock(side_effect=RuntimeError("economy failed")))
    wiring.economy_http = SimpleNamespace(aclose=AsyncMock())
    with pytest.raises(RuntimeError, match="economy failed"):
        await wiring.close_economy()
    wiring.economy_http.aclose.assert_awaited_once()


def test_importing_factory_does_not_construct_application():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from unittest.mock import patch\n"
            "with patch('ase.container.Container') as constructor:\n"
            "    import ase.app_factory\n"
            "    import ase.cli\n"
            "    constructor.assert_not_called()\n",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
