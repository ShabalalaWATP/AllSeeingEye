"""Operator resets wake polls without overlapping requests or bypassing provider waits."""

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
from unittest.mock import patch

import pytest

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.health import HealthRegistry
from ase.application.feeds.pipeline import Pipeline
from ase.application.feeds.scheduler import FeedScheduler
from ase.application.ports.feed_diagnostics import FeedRateLimited
from feeds_helpers import NOW, FakeClock, FakeConnector


def build(connector, sleep, *, jitter=0):
    clock = FakeClock(NOW)
    health = HealthRegistry()
    scheduler = FeedScheduler(
        [connector],
        Pipeline([]),
        InMemoryEventStore(),
        InMemoryEventBus(),
        health,
        clock,
        sleep=sleep,
        jitter=jitter,
    )
    return scheduler, clock, health


async def turns():
    for _ in range(30):
        await asyncio.sleep(0)


async def test_reset_wakes_an_ordinary_feed_sleeping_after_failure():
    connector = FakeConnector()
    connector.failures = 1

    async def sleep(seconds):
        if seconds:
            await asyncio.Event().wait()

    scheduler, _, health = build(connector, sleep)
    await scheduler.start()
    try:
        await turns()
        assert connector.calls == 1
        scheduler.resume(connector.spec.id)
        await turns()
        assert connector.calls == 2
        assert health.get(connector.spec.id).last_success == NOW
    finally:
        await scheduler.stop()


@pytest.mark.parametrize("immediate_second_reset", [False, True])
async def test_reset_waits_for_cancelled_fetch_cleanup_before_restarting(immediate_second_reset):
    cleanup = asyncio.Event()
    cancelled = asyncio.Event()

    class Connector(FakeConnector):
        async def fetch(self):
            self.calls += 1
            if self.calls == 1:
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()
                    await cleanup.wait()
            return []

    connector = Connector()

    async def sleep(seconds):
        if seconds:
            await asyncio.Event().wait()

    scheduler, _, _ = build(connector, sleep)
    await scheduler.start()
    try:
        await turns()
        scheduler.resume(connector.spec.id)
        if immediate_second_reset:
            scheduler.resume(connector.spec.id)
        await turns()
        assert cancelled.is_set()
        assert connector.calls == 1
        # A second reset must not interrupt the first fetch's cancellation cleanup.
        scheduler.resume(connector.spec.id)
        await turns()
        assert connector.calls == 1
        cleanup.set()
        await turns()
        assert connector.calls == 2
    finally:
        cleanup.set()
        await scheduler.stop()


async def test_retry_after_starts_at_response_and_negative_jitter_cannot_shorten_it():
    class Connector(FakeConnector):
        async def fetch(self):
            clock.advance(timedelta(seconds=30))
            raise FeedRateLimited("Throttled", timedelta(seconds=600))

    connector = Connector()
    sleeps = []

    async def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            scheduler._stopping.set()

    scheduler, clock, health = build(connector, sleep, jitter=0.1)
    with patch("ase.application.feeds.scheduler.random.uniform", side_effect=lambda low, high: low):
        await scheduler._run_connector(connector)
    assert health.get(connector.spec.id).next_poll_at == NOW + timedelta(seconds=630)
    assert sleeps[1] >= 600


async def test_reset_and_direct_poll_preserve_upstream_cooldown():
    class Connector(FakeConnector):
        async def fetch(self):
            self.calls += 1
            if self.calls == 1:
                raise FeedRateLimited("Throttled", timedelta(seconds=600))
            return []

    async def sleep(seconds):
        if seconds:
            await asyncio.Event().wait()

    connector = Connector()
    scheduler, clock, health = build(connector, sleep)
    await scheduler.poll_once(connector)
    scheduler.resume(connector.spec.id)
    await scheduler.poll_once(connector)
    assert connector.calls == 1
    assert health.get(connector.spec.id).next_poll_at == NOW + timedelta(seconds=600)
    clock.advance(timedelta(seconds=600))
    assert (await scheduler.poll_once(connector)).ok
    assert connector.calls == 2


@pytest.mark.parametrize("current", [False, True])
async def test_guarded_rate_limits_keep_deadlines_only_for_current_configuration(current):
    class Connector(FakeConnector):
        async def current_generation(self):
            return 1

        async def fetch_batch(self):
            clock.advance(timedelta(seconds=30))
            raise FeedRateLimited("Sensitive upstream error", timedelta(seconds=600))

        @asynccontextmanager
        async def release_guard(self, generation):
            assert generation == 1
            yield current

    connector = Connector()
    scheduler, clock, health = build(connector, asyncio.sleep)
    outcome = await scheduler.poll_once(connector)
    assert not outcome.ok
    assert "Sensitive" not in (outcome.error or "")
    entry = health.get(connector.spec.id)
    assert entry.polls == int(current)
    assert entry.next_poll_at == (NOW + timedelta(seconds=630) if current else None)
    if current:
        scheduler.resume(connector.spec.id)
        assert health.get(connector.spec.id).next_poll_at == NOW + timedelta(seconds=630)
