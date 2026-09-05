"""Normaliser, health registry, circuit breaker, bus and the scheduler loop."""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.health import CircuitBreaker, HealthRegistry, SourceStatus
from ase.application.feeds.pipeline import Normaliser, Pipeline, clean_text, safe_url
from ase.application.feeds.scheduler import FeedScheduler
from ase.application.ports.feeds import BusMessage
from ase.domain.errors import NotFound
from feeds_helpers import NOW, FakeClock, FakeConnector, make_event, make_spec


def test_clean_text_bounds_and_strips() -> None:
    assert clean_text("  Hello\x00 \n world  ", 100) == "Hello world"
    assert clean_text("", 10) is None
    assert clean_text(None, 10) is None
    assert clean_text("x" * 20, 10) == "xxxxxxxxx…"


def test_markup_is_stripped_and_only_http_links_survive() -> None:
    assert (
        clean_text("<b>Bold</b> &amp; <script>alert(1)</script> text", 100)
        == "Bold & alert(1) text"
    )
    assert clean_text("<p></p>", 10) is None
    assert safe_url(None) is None
    assert safe_url("javascript:alert(1)") is None
    assert safe_url("/relative/path") is None
    assert safe_url("https://" + "x" * 3000) is None
    assert safe_url("  https://example.org/a?b=1 ") == "https://example.org/a?b=1"
    event = make_event("h", title="<i>Quake</i>", summary="<div>Ten km</div>").with_changes(
        url="javascript:x"
    )
    out = Normaliser().process([event])[0]
    assert out.title == "Quake" and out.summary == "Ten km" and out.url is None


def test_normaliser_drops_untitled_and_duplicates() -> None:
    stage = Normaliser()
    events = [
        make_event("a", title=" Title \t one "),
        make_event("a"),
        make_event("b", title="\x01"),
        make_event("c").with_changes(content_hash=""),
    ]
    result = Pipeline([stage]).run(events)
    assert [e.title for e in result] == ["Title one", "Test event"]
    assert result[1].content_hash != ""


def test_circuit_breaker_backoff_and_disable() -> None:
    breaker = CircuitBreaker(disable_after=3, base_backoff=timedelta(seconds=10))
    assert breaker.backoff_for(1) == timedelta(seconds=10)
    assert breaker.backoff_for(2) == timedelta(seconds=20)
    assert breaker.backoff_for(30) == timedelta(hours=1)
    assert not breaker.should_disable(2)
    assert breaker.should_disable(3)


def test_health_registry_transitions() -> None:
    registry = HealthRegistry(breaker=CircuitBreaker(disable_after=2))
    ok = registry.record_success("s", 5, 12.5, NOW, timedelta(minutes=1))
    assert ok.status is SourceStatus.HEALTHY
    assert ok.next_poll_at == NOW + timedelta(minutes=1)
    degraded = registry.record_failure("s", "boom", NOW)
    assert degraded.status is SourceStatus.DEGRADED
    assert degraded.next_poll_at == NOW + timedelta(seconds=60)
    disabled = registry.record_failure("s", "boom again", NOW)
    assert disabled.status is SourceStatus.DISABLED
    assert disabled.next_poll_at is None
    assert registry.reset("s").status is SourceStatus.IDLE
    assert [h.source_id for h in registry.snapshot()] == ["s"]


async def test_bus_fanout_and_overflow() -> None:
    bus = InMemoryEventBus(max_queue=2)
    subscription = bus.subscribe()
    for index in range(4):
        await bus.publish(BusMessage("tick", {"n": index}))
    assert subscription.dropped == 2
    received = []
    subscription.close()
    async for message in subscription:
        received.append(message.payload["n"])
    assert received == [2, 3]
    assert bus.subscriber_count == 0
    await bus.publish(BusMessage("after-close"))


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(NOW)


def build_scheduler(
    connectors: list[FakeConnector], clock: FakeClock, sleeps: list[float] | None = None
) -> tuple[FeedScheduler, InMemoryEventStore, InMemoryEventBus, HealthRegistry]:
    store = InMemoryEventStore()
    bus = InMemoryEventBus()
    health = HealthRegistry(
        breaker=CircuitBreaker(disable_after=2, base_backoff=timedelta(seconds=5))
    )
    recorded = sleeps if sleeps is not None else []

    async def fake_sleep(seconds: float) -> None:
        recorded.append(seconds)
        clock.advance(timedelta(seconds=seconds))
        await asyncio.sleep(0)

    scheduler = FeedScheduler(
        connectors,
        Pipeline([Normaliser()]),
        store,
        bus,
        health,
        clock,
        fetch_timeout=timedelta(seconds=1),
        prune_interval=timedelta(seconds=30),
        jitter=0.0,
        sleep=fake_sleep,
    )
    return scheduler, store, bus, health


async def test_poll_once_success_publishes_changes(clock: FakeClock) -> None:
    connector = FakeConnector(events=[make_event("a"), make_event("b")])
    scheduler, store, bus, health = build_scheduler([connector], clock)
    subscription = bus.subscribe()
    outcome = await scheduler.poll_once(connector)
    assert outcome.ok and outcome.fetched == 2 and outcome.changed == 2
    assert store.stats().total == 2
    assert health.get("test_source").status is SourceStatus.HEALTHY
    subscription.close()
    kinds = [m.kind async for m in subscription]
    assert kinds == ["event.upsert", "source.health"]
    # A second identical poll changes nothing and publishes only health.
    subscription = bus.subscribe()
    outcome = await scheduler.poll_once(connector)
    assert outcome.changed == 0
    subscription.close()
    assert [m.kind async for m in subscription] == ["source.health"]


async def test_poll_once_failure_and_timeout(clock: FakeClock) -> None:
    connector = FakeConnector()
    connector.failures = 1
    scheduler, _, _, health = build_scheduler([connector], clock)
    outcome = await scheduler.poll_once(connector)
    assert not outcome.ok
    assert outcome.error is not None and "upstream exploded" in outcome.error
    assert health.get("test_source").status is SourceStatus.DEGRADED

    class SlowConnector(FakeConnector):
        async def fetch(self) -> list:  # type: ignore[override]
            await asyncio.sleep(5)
            return []

    slow = SlowConnector(make_spec("slow"))
    scheduler, _, _, health = build_scheduler([slow], clock)
    outcome = await scheduler.poll_once(slow)
    assert not outcome.ok
    assert "TimeoutError" in (outcome.error or "")


async def test_run_loop_backs_off_then_disables_and_resumes(clock: FakeClock) -> None:
    connector = FakeConnector()
    connector.failures = 2
    sleeps: list[float] = []
    scheduler, store, _, health = build_scheduler([connector], clock, sleeps)
    await scheduler.start()
    assert scheduler.running
    for _ in range(20):
        await asyncio.sleep(0)
    assert health.get("test_source").status is SourceStatus.DISABLED
    assert connector.calls == 2
    assert 5.0 in sleeps  # the first failure waits one base backoff before retrying
    scheduler.resume("test_source")
    for _ in range(20):
        await asyncio.sleep(0)
    assert connector.calls >= 3
    assert health.get("test_source").status is SourceStatus.HEALTHY
    assert store.stats().total == 1
    with pytest.raises(NotFound):
        scheduler.resume("unknown")
    await scheduler.stop()
    assert not scheduler.running


async def test_prune_loop_publishes_expiries(clock: FakeClock) -> None:
    connector = FakeConnector(events=[make_event("old", observed_at=NOW - timedelta(days=30))])
    scheduler, store, bus, _ = build_scheduler([connector], clock)
    subscription = bus.subscribe()
    await scheduler.start()
    for _ in range(30):
        await asyncio.sleep(0)
    await scheduler.stop()
    subscription.close()
    kinds = [m.kind async for m in subscription]
    assert "event.expire" in kinds
    assert store.stats().total == 0
