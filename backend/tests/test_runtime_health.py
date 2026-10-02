"""Liveness observes completed work, excludes disabled workers and fences admin data."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.worker_health import InMemoryWorkerHeartbeats, LoopLag
from ase.application.conflict_screening.queue import ConflictScreeningQueue
from ase.application.feeds.scheduler import FeedScheduler
from ase.application.ports.feeds import BusMessage
from ase.application.worker_progress import run_cycle, worker_heartbeats
from ase.container.runtime_health import RuntimeHealth
from feeds_helpers import FakeConnector, make_spec
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token


def test_three_intervals_allow_idle_progress_but_detect_stall():
    now = 0.0
    workers = InMemoryWorkerHeartbeats(monotonic=lambda: now)
    workers.register("idle", 10)
    assert workers.ready
    now = 30
    assert workers.ready
    now += 0.001
    assert not workers.ready
    workers.completed("idle", 10)
    assert workers.ready
    assert workers.snapshot()[0].last_cycle is not None
    assert {item.name for item in workers.snapshot()} == {"idle"}


@pytest.mark.parametrize("interval", [0, -1, float("inf"), float("nan")])
def test_invalid_intervals_are_rejected(interval):
    with pytest.raises(ValueError):
        InMemoryWorkerHeartbeats().register("bad", interval)


def test_resuming_a_worker_shortens_allowance_without_fabricating_progress():
    now = 0.0
    registry = InMemoryWorkerHeartbeats(monotonic=lambda: now)
    registry.register("feed:paused", 86400)
    now = 600
    registry.register("feed:paused", 180)
    assert not registry.ready
    assert registry.snapshot()[0].last_cycle is None


async def test_progress_is_not_stamped_while_a_cycle_is_blocked():
    now = 0.0
    registry = InMemoryWorkerHeartbeats(monotonic=lambda: now)
    binding = worker_heartbeats.set(registry)
    release = asyncio.Event()
    task = asyncio.create_task(run_cycle("blocked", 10, release.wait))
    try:
        await asyncio.sleep(0)
        now = 31
        assert not registry.ready
        assert registry.snapshot()[0].last_cycle is None
        release.set()
        await task
        assert registry.ready
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        worker_heartbeats.reset(binding)


async def test_failed_cycle_records_only_safe_code_and_cancelled_cycle_is_not_progress():
    registry = InMemoryWorkerHeartbeats()
    binding = worker_heartbeats.set(registry)
    try:
        with pytest.raises(RuntimeError):
            await run_cycle("failed", 10, AsyncMock(side_effect=RuntimeError("private-provider")))
        with pytest.raises(asyncio.CancelledError):
            await run_cycle("cancelled", 10, AsyncMock(side_effect=asyncio.CancelledError))
        items = {item.name: item for item in registry.snapshot()}
        assert items["failed"].last_error_code == "cycle_failed"
        assert items["cancelled"].last_cycle is None
        assert "private-provider" not in str(items)
    finally:
        worker_heartbeats.reset(binding)


async def test_cancelled_scheduler_degrades_readiness_after_three_intervals(app, client, container):
    now = 0.0
    registry = InMemoryWorkerHeartbeats(monotonic=lambda: now)
    app.state.runtime = RuntimeHealth(workers=registry)
    scheduler = FeedScheduler(
        [],
        container.pipeline,
        container.store,
        container.bus,
        container.health,
        container.clock,
        prune_interval=timedelta(seconds=1),
    )
    binding = worker_heartbeats.set(registry)
    try:
        await scheduler.start()
        await asyncio.sleep(0)
        assert (await client.get("/api/ready")).status_code == 200
        await scheduler.stop()
        now = 3.001
        response = await client.get("/api/ready")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "not_ready"
        assert "scheduler" not in response.text
        assert [item.name for item in registry.snapshot()] == ["scheduler"]
    finally:
        await scheduler.stop()
        worker_heartbeats.reset(binding)


async def test_source_resume_outside_lifespan_retains_worker_registry(container):
    now = 0.0
    registry = InMemoryWorkerHeartbeats(monotonic=lambda: now)
    cycle = asyncio.Event()

    async def sleep(seconds):
        if seconds == 0:
            return
        if seconds < 3600:
            cycle.set()
        await asyncio.Event().wait()

    source = FakeConnector(make_spec("resumed"))
    scheduler = FeedScheduler(
        [source],
        container.pipeline,
        container.store,
        container.bus,
        container.health,
        container.clock,
        first_poll_spread=timedelta(),
        prune_interval=timedelta(hours=1),
        sleep=sleep,
    )
    binding = worker_heartbeats.set(registry)
    await scheduler.start()
    worker_heartbeats.reset(binding)
    try:
        await asyncio.wait_for(cycle.wait(), 2)
        now = 1000
        assert not registry.ready
        cycle.clear()
        # Administrative requests do not carry the lifespan's heartbeat context.
        assert worker_heartbeats.get() is None
        scheduler.resume("resumed")
        await asyncio.wait_for(cycle.wait(), 2)
        assert registry.ready
    finally:
        await scheduler.stop()


async def test_loop_lag_degrades_public_readiness(app, client):
    lag = LoopLag()
    lag._samples.extend([3.0] * 120)
    app.state.runtime = RuntimeHealth(lag=lag)
    response = await client.get("/api/ready")
    assert response.status_code == 503
    assert "lag" not in response.text


async def test_intentionally_disabled_worker_is_not_registered():
    registry = InMemoryWorkerHeartbeats()
    binding = worker_heartbeats.set(registry)
    worker = ConflictScreeningQueue(None, None, None, None, None, None, enabled=False)
    try:
        await worker.start()
        await asyncio.sleep(0)
        assert registry.snapshot() == []
        assert registry.ready
    finally:
        await worker.stop()
        worker_heartbeats.reset(binding)


async def test_stream_drops_survive_subscription_close():
    bus = InMemoryEventBus(max_queue=1)
    subscription = bus.subscribe()
    await bus.publish(BusMessage("source.health"))
    await bus.publish(BusMessage("source.health"))
    assert bus.queue_depth == 1
    assert bus.dropped_count == 1
    subscription.close()
    subscription.close()
    assert bus.subscriber_count == 0
    assert bus.dropped_count == 1


async def test_runtime_is_admin_only_and_has_no_private_fields(app, client, user, admin):
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    assert (await client.get("/api/admin/runtime", headers=bearer(user_token))).status_code == 403
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    app.state.runtime.workers.completed("scheduler", 60, "cycle_failed")
    response = await client.get("/api/admin/runtime", headers=bearer(admin_token))
    assert response.status_code == 200
    data = response.json()
    assert data["workers"][0]["last_error_code"] == "cycle_failed"
    assert data["job_queue_depth"] == 0
    assert data["stream_drops"] == 0
    assert data["store_budget_bytes"] > 0
    assert not {"url", "provider", "secret", "error_text"}.intersection(data)
