"""Bulk feed updates name their affected partitions, and each stream sees only its own."""

from __future__ import annotations

import json

import pytest

from ase.adapters.bus.memory import MAX_UPSERT_EVENTS, InMemoryEventBus, soft_invalidation
from ase.adapters.store.memory import InMemoryEventStore
from ase.api.stream_encoding import StreamEncoder, serialise
from ase.application.feeds.health import HealthRegistry
from ase.application.feeds.pipeline import Pipeline
from ase.application.feeds.scheduler import FeedScheduler
from ase.application.ports.feeds import BusMessage
from ase.domain.events import Category, Event
from feeds_helpers import NOW, FakeClock, FakeConnector, make_event, make_spec

MARITIME = frozenset({Category.MARITIME})
UNRELATED = frozenset({Category.DISASTER, Category.CYBER})


def vessels(count: int = MAX_UPSERT_EVENTS + 1) -> list[Event]:
    return [
        make_event(f"v{i}", source_id="aisstream", category=Category.MARITIME, subtype="vessel")
        for i in range(count)
    ]


async def published(events: list[object], source_id: str | None = "aisstream") -> BusMessage:
    bus = InMemoryEventBus()
    subscription = bus.subscribe()
    await bus.publish(BusMessage("event.upsert", {"source_id": source_id, "events": events}))
    message = await anext(subscription)
    subscription.close()
    return message


async def test_a_maritime_bulk_update_names_only_the_maritime_partition() -> None:
    message = await published(list(vessels()))
    assert message.kind == "event.resync"
    assert dict(message.payload) == {
        "reason": "snapshot_required",
        "categories": (Category.MARITIME,),
        "source_id": "aisstream",
    }
    assert serialise(message, frozenset()) == {
        "reason": "snapshot_required",
        "categories": ["maritime"],
        "source_id": "aisstream",
    }
    assert serialise(message, MARITIME | {Category.AVIATION}) == serialise(message, frozenset())
    # A browser filtered exclusively to unrelated categories is not told to refresh.
    assert serialise(message, UNRELATED) is None


async def test_mixed_batches_name_every_partition_and_narrow_to_each_filter() -> None:
    neighbour = make_event("regraded", category=Category.NEWS)
    message = await published([*vessels(), neighbour])
    assert message.payload["categories"] == (Category.MARITIME, Category.NEWS)
    assert serialise(message, frozenset({Category.NEWS, Category.CYBER})) == {
        "reason": "snapshot_required",
        "categories": ["news"],
        "source_id": "aisstream",
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"events": [*vessels(), "not an event"]},
        {"events": "not a list"},
        {"events": []},
    ],
)
def test_unrecognised_batches_fall_back_to_a_full_reconciliation(payload: dict) -> None:
    message = soft_invalidation(BusMessage("event.upsert", payload))
    assert dict(message.payload) == {"reason": "snapshot_required"}
    # Every subscriber, including a narrowly filtered one, reconciles fully.
    for wanted in (frozenset(), MARITIME, UNRELATED):
        assert serialise(message, wanted) == {"reason": "snapshot_required"}


@pytest.mark.parametrize(
    "categories", [("maritime",), (), None, (Category.MARITIME, "space"), "maritime"]
)
def test_malformed_partition_metadata_is_treated_as_unknown(categories: object) -> None:
    message = BusMessage("event.resync", {"reason": "snapshot_required", "categories": categories})
    assert serialise(message, UNRELATED) == {"reason": "snapshot_required"}


@pytest.mark.parametrize("reason", ["stream_gap", "expiry_overflow"])
def test_gaps_still_reach_every_filter_without_partitions(reason: str) -> None:
    message = BusMessage(
        "event.resync", {"reason": reason, "categories": (Category.MARITIME,), "source_id": "x"}
    )
    for wanted in (frozenset(), MARITIME, UNRELATED):
        assert serialise(message, wanted) == {"reason": reason}


async def test_shared_hint_text_matches_per_client_json_and_is_encoded_once_per_filter() -> None:
    message = await published(list(vessels()))
    encoder = StreamEncoder()
    for wanted in (frozenset(), MARITIME, UNRELATED, MARITIME):
        payload = serialise(message, wanted)
        expected = None if payload is None else json.dumps(payload, ensure_ascii=False)
        assert encoder.encode(message, wanted) == expected
    assert encoder.encoded == 3


async def test_regraded_neighbours_from_a_bulk_poll_are_named_as_affected() -> None:
    store = InMemoryEventStore()
    neighbour = make_event("story", source_id="wire", category=Category.NEWS)
    store.upsert([neighbour])
    graded = neighbour.with_changes(story_id="story-1")

    class NeighbourGrader:
        def regrade(self, events: list[Event]) -> list[Event]:
            store.put([graded])
            return [graded]

    bus = InMemoryEventBus()
    subscription = bus.subscribe()
    connector = FakeConnector(make_spec("aisstream"), vessels())
    scheduler = FeedScheduler(
        [connector],
        Pipeline([]),
        store,
        bus,
        HealthRegistry(),
        FakeClock(NOW),
        grader=NeighbourGrader(),
    )
    outcome = await scheduler.poll_once(connector)
    assert outcome.ok
    hint = await anext(subscription)
    subscription.close()
    assert hint.kind == "event.resync"
    assert hint.payload["categories"] == (Category.MARITIME, Category.NEWS)
