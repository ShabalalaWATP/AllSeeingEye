"""Independent housekeeping never activates providers or reconciles held AI work."""

import asyncio
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from structlog.testing import capture_logs

from ai_usage_helpers import add_policy, policy
from ase.adapters.persistence.ai_usage_models import AiUsageCounterRow, AiUsageReservationRow
from ase.adapters.worker_health import InMemoryWorkerHeartbeats
from ase.app_lifecycle import lifespan
from ase.application.worker_progress import worker_heartbeats
from ase.container.dormant_retention import DormantRetention, _cycle, run_dormant_retention
from ase.domain.ai_usage import PERIOD_RETENTION, RESERVATION_RETENTION
from ase.domain.errors import NotFound
from research_input_helpers import Harness, extracted
from test_ai_usage_pruning import _count, _counter, _ids, _reservation
from test_application_lifecycle import runtime as runtime  # noqa: PLC0414


async def test_dormant_ai_cleanup_preserves_held_and_unknown_reservations(container):
    current = policy()
    await add_policy(container, current)
    age = RESERVATION_RETENTION + timedelta(days=1)
    kept = {
        await _reservation(container, current.id, state, age) for state in ("reserved", "unknown")
    }
    await _reservation(container, current.id, "settled", age)
    await _counter(container, current.id, PERIOD_RETENTION + timedelta(days=1), reserved=1)
    await DormantRetention(container).ai()
    assert await _ids(container, AiUsageReservationRow) == kept
    assert await _count(container, AiUsageCounterRow) == 1


async def test_idle_private_inputs_expire_without_activity_and_preserve_newer_inputs():
    harness = Harness()
    first = harness.store.reserve(harness.actor, "notes.txt")
    parent = harness.store.put(first, extracted())
    pending = harness.store.reserve(harness.actor, "notes.txt")
    harness.clock.advance(timedelta(minutes=1))
    derived = harness.store.reserve(harness.actor, "notes.txt")
    harness.store.put(derived, replace(extracted(), parent_input_id=parent.receipt.id))
    live = harness.store.reserve(harness.actor, "notes.txt")
    harness.store.put(live, extracted())
    harness.clock.advance(timedelta(minutes=14))
    await DormantRetention(SimpleNamespace(research_inputs=harness.store)).private_inputs()
    assert set(harness.store._reservations) == {live.id}
    assert set(harness.store._ready) == {live.id}
    assert set(harness.store._sizes) == {live.id}
    with pytest.raises(NotFound):
        harness.store.put(pending, extracted())


async def test_worker_category_failure_is_sanitised_and_does_not_starve_later_work(monkeypatch):
    calls = []
    for name in ("private_inputs", "selected", "consumed", "alerts", "push", "research", "ai"):

        async def operation(_self, name=name):
            calls.append(name)
            if name == "selected":
                raise RuntimeError("private SQL and credentials")

        monkeypatch.setattr(DormantRetention, name, operation)
    with capture_logs() as logs:
        await DormantRetention(object()).cycle()
    assert calls == ["private_inputs", "selected", "consumed", "alerts", "push", "research", "ai"]
    assert [(r["event"], r["category"]) for r in logs] == [("dormant_retention.failed", "selected")]
    assert "private SQL" not in str(logs)


async def test_cancellation_propagates_without_starting_later_categories(monkeypatch):
    monkeypatch.setattr(
        DormantRetention, "private_inputs", AsyncMock(side_effect=asyncio.CancelledError())
    )
    selected = AsyncMock()
    monkeypatch.setattr(DormantRetention, "selected", selected)
    with pytest.raises(asyncio.CancelledError):
        await DormantRetention(object()).cycle()
    selected.assert_not_awaited()


async def test_unconfigured_idle_installation_runs_cleanup_without_starting_delivery(
    container, monkeypatch
):
    monkeypatch.setattr(
        "ase.container.web_push.push_sender", Mock(side_effect=AssertionError("provider started"))
    )
    # A missing selected gate is a category-local failure in this unmigrated fixture.
    # Real deployments seed it through migrations; every other phase must run.
    with capture_logs() as logs:
        await DormantRetention(container).cycle()
    assert [r["category"] for r in logs if r["event"] == "dormant_retention.failed"] == ["selected"]


async def test_lifespan_owns_dormant_worker_when_optional_work_is_disabled(runtime, monkeypatch):
    app, container, tasks = runtime
    container.settings.feeds_enabled = False
    started = asyncio.Event()

    async def worker(current):
        assert current is container
        tasks.append(asyncio.current_task())
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr("ase.app_lifecycle.run_dormant_retention", worker)
    async with lifespan(app):
        await asyncio.wait_for(started.wait(), 10)
    assert all(task.done() for task in tasks)
    container.scheduler.start.assert_not_awaited()
    container.dispose.assert_awaited_once()


async def test_timeout_records_failure_heartbeat_and_remains_cancellable(monkeypatch):
    registry = InMemoryWorkerHeartbeats()
    binding = worker_heartbeats.set(registry)
    monkeypatch.setattr("ase.container.dormant_retention.PHASE_TIMEOUT_SECONDS", 0.01)
    try:
        with capture_logs() as logs:
            await _cycle("selected", asyncio.Event().wait)
        [state] = registry.snapshot()
        assert state.last_cycle is not None and state.last_error_code == "cycle_failed"
        assert not state.overdue and registry.ready
        assert logs[0]["category"] == "selected"
    finally:
        worker_heartbeats.reset(binding)


async def test_category_timers_progress_independently_and_shutdown_joins_every_child(monkeypatch):
    tasks = {}
    all_started = asyncio.Event()
    completed = set()
    for name in ("private_inputs", "selected", "consumed", "alerts", "push", "research", "ai"):

        async def operation(_self, name=name):
            tasks[name] = asyncio.current_task()
            if len(tasks) == 7:
                all_started.set()
            if name == "selected":
                await asyncio.Event().wait()
            completed.add(name)

        monkeypatch.setattr(DormantRetention, name, operation)
    parent = asyncio.create_task(run_dormant_retention(object()))
    try:
        await asyncio.wait_for(all_started.wait(), 10)
        assert completed == {"private_inputs", "consumed", "alerts", "push", "research", "ai"}
        assert len(set(tasks.values())) == 7
    finally:
        parent.cancel()
        with pytest.raises(asyncio.CancelledError):
            await parent
    assert all(task.done() for task in tasks.values())
