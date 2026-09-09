"""Deterministic bounds for ingestion, snapshots and slow live subscribers."""

import asyncio
import json
from datetime import timedelta

import pytest

from ase.adapters.bus.memory import MAX_UPSERT_BYTES, MAX_UPSERT_EVENTS, InMemoryEventBus
from ase.adapters.store import query as store_query
from ase.adapters.store.memory import InMemoryEventStore, estimate_bytes
from ase.api.routers.stream import serialise
from ase.application.feeds.pipeline import Normaliser, Pipeline
from ase.application.ports.feeds import BusMessage, EventQuery
from ase.domain.events import Category, freeze_attributes
from feeds_helpers import NOW, make_event


async def test_large_publication_is_one_small_resync_for_each_subscriber() -> None:
    bus = InMemoryEventBus()
    subscribers = [bus.subscribe(), bus.subscribe()]
    events = [make_event(str(i)) for i in range(MAX_UPSERT_EVENTS + 1)]
    await bus.publish(BusMessage("event.upsert", {"events": events}))
    for subscriber in subscribers:
        message = await anext(subscriber)
        assert message.kind == "event.resync"
        assert message.payload == {"reason": "snapshot_required"}
        subscriber.close()
        with pytest.raises(StopAsyncIteration):
            await anext(subscriber)


async def test_bounded_small_delta_is_preserved() -> None:
    bus = InMemoryEventBus()
    subscriber = bus.subscribe()
    events = [make_event(str(i)) for i in range(100)]
    message = BusMessage("event.upsert", {"events": events})
    await bus.publish(message)
    assert await anext(subscriber) is message
    subscriber.close()


async def test_default_slow_subscriber_queue_is_bounded() -> None:
    bus = InMemoryEventBus()
    subscriber = bus.subscribe()
    for index in range(256):
        await bus.publish(BusMessage("source.health", {"index": index}))
    assert subscriber.dropped == 128
    assert (await anext(subscriber)).payload == {"index": 128}
    subscriber.close()


async def test_bulk_refresh_lost_to_queue_overflow_becomes_real_gap() -> None:
    bus = InMemoryEventBus(max_queue=1)
    subscriber = bus.subscribe()
    await bus.publish(BusMessage("event.upsert", {"events": [make_event()] * 501}))
    await bus.publish(BusMessage("source.health", {}))
    assert (await anext(subscriber)).payload == {"reason": "stream_gap"}
    assert (await anext(subscriber)).kind == "source.health"
    subscriber.close()


async def test_heavy_payload_is_bounded_even_below_event_count_limit() -> None:
    bus = InMemoryEventBus()
    subscriber = bus.subscribe()
    heavy = make_event().with_changes(
        attributes=freeze_attributes({f"field-{i}": "x" * 500 for i in range(40)})
    )
    await bus.publish(BusMessage("event.upsert", {"events": [heavy] * 20}))
    assert (await anext(subscriber)).kind == "event.resync"
    subscriber.close()


@pytest.mark.parametrize("text", ["\x01" * 500, "🌍" * 500, '"\\' * 250])
async def test_wire_payload_keeps_headroom_below_browser_byte_limit(text: str) -> None:
    event = make_event().with_changes(attributes=freeze_attributes({"value": text}))
    count = min(MAX_UPSERT_EVENTS, MAX_UPSERT_BYTES // estimate_bytes(event))
    bus = InMemoryEventBus()
    subscriber = bus.subscribe()
    await bus.publish(BusMessage("event.upsert", {"events": [event] * count}))
    message = await anext(subscriber)
    assert message.kind == "event.upsert"
    wire = json.dumps(serialise(message, frozenset()), ensure_ascii=False).encode("utf-8")
    assert len(wire) + 100 < 1024 * 1024
    subscriber.close()


async def test_pipeline_yields_and_preserves_global_duplicates() -> None:
    pipeline = Pipeline([Normaliser()])
    events = [make_event(str(i)) for i in range(501)]
    events.insert(0, make_event("later", title=" "))
    events.extend([make_event("later"), make_event("0", title="Duplicate")])
    checkpoints = []
    task = asyncio.create_task(pipeline.run_cooperatively(events))
    while not task.done():
        checkpoints.append(True)
        await asyncio.sleep(0)
    assert len(checkpoints) >= 3
    assert await task == pipeline.run(events)


def test_source_snapshot_checks_only_indexed_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    store = InMemoryEventStore()
    store.upsert([make_event(str(i), source_id="large") for i in range(1000)])
    target = [make_event(str(i), source_id="target", country_iso="GB") for i in range(10)]
    store.upsert(target)
    examined = []
    original = store_query.evidence_matches_time

    def counted(*args, **kwargs):
        examined.append(args[0].id)
        return original(*args, **kwargs)

    monkeypatch.setattr(store_query, "evidence_matches_time", counted)
    assert len(store.query(EventQuery(source_ids=frozenset({"target"}), limit=3))) == 3
    assert len(examined) == 10
    assert not store.query(EventQuery(source_ids=frozenset({"missing"})))
    assert len(store.query(EventQuery(source_ids=frozenset({"target"}), country_iso="gb"))) == 10
    assert not store.query(EventQuery(source_ids=frozenset({"target"}), country_iso="US"))
    assert not store.query(
        EventQuery(source_ids=frozenset({"target"}), categories=frozenset({Category.NEWS}))
    )


def test_source_index_updates_and_prunes_without_stale_ids() -> None:
    store = InMemoryEventStore()
    event = make_event("one", source_id="before", observed_at=NOW - timedelta(days=10))
    store.put([event])
    updated = event.with_changes(source_id="after")
    store.put([updated])
    assert not store.query(EventQuery(source_ids=frozenset({"before"})))
    assert store.query(EventQuery(source_ids=frozenset({"after"}))) == [updated]
    store.prune(NOW)
    assert not store.query(EventQuery(source_ids=frozenset({"after"})))


def test_top_k_snapshot_matches_complete_order() -> None:
    store = InMemoryEventStore()
    store.put([make_event(str(i), published_at=NOW - timedelta(minutes=i % 7)) for i in range(100)])
    complete = store.query(EventQuery(limit=100))
    assert store.query(EventQuery(limit=7)) == complete[:7]


def test_estimate_includes_grades_and_unicode_storage() -> None:
    event = make_event()
    assert estimate_bytes(event) > 1024
    changed = event.with_changes(grade_rationale="x" * 100, story_id="x" * 50)
    assert estimate_bytes(changed) - estimate_bytes(event) == 4 * (
        100 - len(event.grade_rationale) + 50
    )
