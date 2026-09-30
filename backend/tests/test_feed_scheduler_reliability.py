"""Bounded processing, a global fetch cap and staggered start-up polls."""

import asyncio
from collections import Counter
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import timedelta

import pytest
from pydantic import ValidationError

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.cadence import first_poll_delay, next_poll_delay
from ase.application.feeds.health import HealthRegistry, SourceStatus
from ase.application.feeds.pipeline import Normaliser, Pipeline
from ase.application.feeds.scheduler import FeedScheduler
from ase.domain.events import event_id
from ase.infrastructure.settings import Settings
from feeds_helpers import NOW, FakeClock, FakeConnector, make_event, make_spec


class Admission:
    """An in-memory source admission; one source may stall its final, guarded read."""

    def __init__(self, stall_on: str | None = None) -> None:
        self.lock = asyncio.Lock()
        self.disabled: set[str] = set()
        self.stall_on = stall_on
        self.stalled = asyncio.Event()
        self.checks: Counter[str] = Counter()

    @asynccontextmanager
    async def guard(self):
        async with self.lock:
            yield

    async def enabled(self, source_id: str) -> bool:
        self.checks[source_id] += 1
        if source_id == self.stall_on and self.checks[source_id] == 2:
            self.stalled.set()
            await asyncio.Event().wait()
        return source_id not in self.disabled

    async def enabled_many(self, source_ids: tuple[str, ...]) -> dict[str, bool]:
        return {source_id: source_id not in self.disabled for source_id in source_ids}


def scheduler_for(connectors, *, clock=None, health=None, **options):
    store = InMemoryEventStore()
    scheduler = FeedScheduler(
        connectors,
        Pipeline([Normaliser()]),
        store,
        InMemoryEventBus(),
        health or HealthRegistry(),
        clock or FakeClock(NOW),
        **options,
    )
    return scheduler, store


def connector(source_id: str, **spec) -> FakeConnector:
    return FakeConnector(
        replace(make_spec(source_id), **spec), [make_event(source_id, source_id=source_id)]
    )


async def turns(count: int = 30) -> None:
    for _ in range(count):
        await asyncio.sleep(0)


async def test_hung_processing_fails_that_source_while_others_keep_publishing() -> None:
    slow, fast = connector("slow"), connector("fast")
    admission = Admission(stall_on="slow")
    scheduler, store = scheduler_for(
        [slow, fast], admission=admission, processing_timeout=timedelta(seconds=0.5)
    )
    stalled = asyncio.create_task(scheduler.poll_once(slow))
    await asyncio.wait_for(admission.stalled.wait(), 2)
    # Start the other source's own deadline strictly later than the stalled one.
    await asyncio.sleep(0.2)
    published = await asyncio.wait_for(scheduler.poll_once(fast), 2)
    timed_out = await asyncio.wait_for(stalled, 2)
    assert published.ok and store.get(event_id("fast", "fast")) is not None
    assert not timed_out.ok
    assert timed_out.error == "Processing exceeded its 0.5-second deadline."
    entry = scheduler.poller.health_for("slow")
    assert entry.status is SourceStatus.DEGRADED and entry.consecutive_failures == 1
    assert store.get(event_id("slow", "slow")) is None
    # The guard was released, so the same source recovers on its next poll.
    assert (await asyncio.wait_for(scheduler.poll_once(slow), 2)).ok
    assert not admission.lock.locked()


async def test_guarded_failure_verification_is_bounded_too() -> None:
    class Hanging(FakeConnector):
        async def current_generation(self) -> int:
            return 1

        async def fetch_batch(self):
            raise RuntimeError("upstream down")

        @asynccontextmanager
        async def release_guard(self, generation: int):
            await asyncio.Event().wait()
            yield True

    admission = Admission()
    hanging = Hanging(make_spec("guarded"))
    scheduler, _ = scheduler_for(
        [hanging], admission=admission, processing_timeout=timedelta(seconds=0.05)
    )
    outcome = await asyncio.wait_for(scheduler.poll_once(hanging), 2)
    assert outcome.error == "Connection verification unavailable."
    assert scheduler.poller.health_for("guarded").polls == 0
    assert not admission.lock.locked()


async def test_fetches_share_one_global_concurrency_cap() -> None:
    gate = asyncio.Event()
    active = peak = 0

    class Blocking(FakeConnector):
        async def fetch(self):
            nonlocal active, peak
            self.calls += 1
            active += 1
            peak = max(peak, active)
            try:
                await gate.wait()
            finally:
                active -= 1
            return []

    connectors = [Blocking(make_spec(f"source_{index}")) for index in range(5)]
    scheduler, _ = scheduler_for(connectors, fetch_concurrency=2)
    polls = [asyncio.create_task(scheduler.poll_once(item)) for item in connectors]
    await turns()
    assert active == 2 and sum(item.calls for item in connectors) == 2
    gate.set()
    outcomes = await asyncio.wait_for(asyncio.gather(*polls), 2)
    assert all(outcome.ok for outcome in outcomes) and peak == 2
    with pytest.raises(ValueError):
        scheduler_for([], fetch_concurrency=0)


def test_fetch_concurrency_setting_is_bounded() -> None:
    assert Settings(_env_file=None, env="test").feed_fetch_concurrency == 16
    for invalid in (0, 65):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, env="test", feed_fetch_concurrency=invalid)


def test_first_polls_spread_within_bounds_with_map_layers_first() -> None:
    spread = timedelta(seconds=60)
    sensor = replace(make_spec("sensor", seconds=30), instrument=True)
    sensors = [first_poll_delay(sensor, spread) for _ in range(300)]
    slow_news = [first_poll_delay(make_spec("news", seconds=900), spread) for _ in range(300)]
    fast_news = [first_poll_delay(make_spec("fast", seconds=40), spread) for _ in range(300)]
    # Each window is uniform(0, min(interval, 60s)); map layers take its first quarter.
    assert all(0 <= delay <= 7.5 for delay in sensors)
    assert all(15 <= delay <= 60 for delay in slow_news)
    assert all(10 <= delay <= 40 for delay in fast_news)
    assert max(sensors) <= min(slow_news)
    assert len(set(slow_news)) > 1
    assert first_poll_delay(make_spec("news", seconds=900), timedelta(0)) == 0


async def test_start_staggers_first_polls_but_a_reset_polls_at_once() -> None:
    sleeps: list[float] = []

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if seconds:
            await asyncio.Event().wait()

    sensor = connector("sensor", instrument=True, poll_interval=timedelta(seconds=30))
    news = connector("news", poll_interval=timedelta(seconds=900))
    scheduler, _ = scheduler_for([sensor, news], sleep=sleep, prune_interval=timedelta(hours=1))
    await scheduler.start()
    try:
        await turns()
        assert 0 <= sleeps[0] <= 7.5 and 15 <= sleeps[1] <= 60 and sleeps[2] == 3600
        assert sensor.calls == news.calls == 0
        scheduler.resume("news")
        await turns()
        assert news.calls == 1 and sensor.calls == 0
    finally:
        await scheduler.stop()


def test_next_poll_delay_honours_future_deadlines_only() -> None:
    entry = HealthRegistry().get("s")
    interval = timedelta(seconds=60)
    assert next_poll_delay(entry, interval, NOW, 0.0) == 60
    entry.next_poll_at = NOW + timedelta(seconds=0.2)
    assert next_poll_delay(entry, interval, NOW, 0.0) == 1.0
    entry.next_poll_at = NOW + timedelta(hours=6)
    assert 6 * 3600 <= next_poll_delay(entry, interval, NOW, 0.1) <= 6 * 3600 * 1.1
    entry.next_poll_at = NOW - timedelta(seconds=5)
    assert next_poll_delay(entry, interval, NOW, 0.0) == 60
