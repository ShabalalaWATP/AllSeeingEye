"""Lossy expiry bookkeeping and subscriber gaps must request a canonical snapshot."""

import asyncio
from datetime import timedelta

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.store import memory
from ase.adapters.store.memory import InMemoryEventStore, estimate_bytes
from ase.api.routers.stream import serialise
from ase.application.ports.feeds import BusMessage
from feeds_helpers import NOW, FakeClock, make_event
from test_pipeline_and_scheduler import build_scheduler


def test_large_expiry_signals_resynchronisation_without_unbounded_ids():
    store = InMemoryEventStore()
    store.upsert(make_event(str(i), observed_at=NOW - timedelta(days=30)) for i in range(10001))
    result = store.prune(NOW)
    assert result.expired == 10001
    assert len(result.ids) <= 10000
    assert result.resync_required
    assert store.stats().total == 0
    assert not store.prune(NOW).resync_required


def test_reinserted_id_is_not_expired_by_old_eviction():
    sample = make_event("a")
    store = InMemoryEventStore(memory_budget_bytes=estimate_bytes(sample) + 10)
    store.upsert([sample])
    store.upsert([make_event("b", observed_at=NOW + timedelta(seconds=1))])
    restored = sample.with_changes(observed_at=NOW + timedelta(seconds=2))
    store.upsert([restored])
    result = store.prune(NOW)
    assert sample.id not in result.ids
    assert store.get(sample.id) == restored


def test_pending_evictions_are_bounded_and_overflow_is_sticky(monkeypatch):
    monkeypatch.setattr(memory, "MAX_PRUNE_IDS", 3)
    store = InMemoryEventStore(memory_budget_bytes=estimate_bytes(make_event("a")) + 10)
    for i in range(20):
        store.upsert([make_event(str(i), observed_at=NOW + timedelta(seconds=i))])
    assert len(store._pending_expiry) <= 3
    result = store.prune(NOW)
    assert result.evicted == 19 and result.resync_required
    assert not store.prune(NOW).resync_required


async def test_overflow_barrier_cannot_be_dropped_and_discards_old_event_deltas():
    bus = InMemoryEventBus(max_queue=2)
    subscription = bus.subscribe()
    for message in (
        BusMessage("event.resync", {"reason": "expiry_overflow"}),
        BusMessage("event.upsert", {"events": [make_event("stale")]}),
        BusMessage("source.health"),
        BusMessage("source.health"),
    ):
        await bus.publish(message)
    first = await anext(subscription)
    assert first.kind == "event.resync" and first.payload == {"reason": "stream_gap"}
    subscription.close()
    remaining = [message async for message in subscription]
    assert all(message.kind != "event.upsert" for message in remaining)


def test_resync_frame_is_category_independent_and_allowlisted():
    assert serialise(BusMessage("event.resync", {"reason": "expiry_overflow"}), frozenset()) == {
        "reason": "expiry_overflow"
    }
    assert serialise(BusMessage("event.resync", {"reason": "secret text"}), frozenset()) is None


async def test_scheduler_publishes_resync_instead_of_incomplete_expiry(monkeypatch):
    monkeypatch.setattr(memory, "MAX_PRUNE_IDS", 1)
    scheduler, store, bus, _ = build_scheduler([], FakeClock(NOW))
    store.upsert([make_event(str(i), observed_at=NOW - timedelta(days=30)) for i in range(3)])
    subscription = bus.subscribe()
    await scheduler.start()
    for _ in range(12):
        await asyncio.sleep(0)
    await scheduler.stop()
    subscription.close()
    messages = [message async for message in subscription]
    assert [message.kind for message in messages] == ["event.resync"]
    assert serialise(messages[0], frozenset()) == {"reason": "expiry_overflow"}
    assert store.stats().total == 0


async def test_waiting_consumer_receives_barrier_before_pre_gap_delta():
    bus = InMemoryEventBus(max_queue=2)
    subscription = bus.subscribe()
    waiting = asyncio.create_task(anext(subscription))
    await asyncio.sleep(0)
    for _ in range(4):
        await bus.publish(BusMessage("event.upsert", {"events": [make_event("stale")]}))
    assert (await waiting).kind == "event.resync"
    fresh = make_event("fresh")
    await bus.publish(BusMessage("event.upsert", {"events": [fresh]}))
    assert (await anext(subscription)).payload["events"][0] == fresh
    subscription.close()
