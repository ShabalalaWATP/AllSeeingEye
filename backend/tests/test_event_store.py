"""The bounded in-memory store: upsert semantics, queries, windows, caps and memory budget."""

from __future__ import annotations

from datetime import timedelta

from ase.adapters.store.memory import InMemoryEventStore, estimate_bytes
from ase.application.feeds.budgets import RetentionBudget
from ase.application.ports.feeds import EventQuery
from ase.domain.events import (
    MAX_ATTRIBUTE_CHARS,
    MAX_ATTRIBUTES,
    BoundingBox,
    Category,
    Point,
    freeze_attributes,
)
from feeds_helpers import NOW, make_event


def test_upsert_counts_and_change_detection() -> None:
    store = InMemoryEventStore()
    first = store.upsert([make_event("a"), make_event("b")])
    assert (first.added, first.updated, first.unchanged) == (2, 0, 0)
    assert set(first.changed_ids) == {make_event("a").id, make_event("b").id}
    second = store.upsert([make_event("a"), make_event("b", version=2, title="Changed")])
    assert (second.added, second.updated, second.unchanged) == (0, 1, 1)
    assert second.changed_ids == (make_event("b").id,)
    assert store.get(make_event("b").id) is not None
    assert store.get(make_event("b").id).title == "Changed"  # type: ignore[union-attr]
    assert store.get("missing") is None


def test_query_filters() -> None:
    store = InMemoryEventStore()
    store.upsert(
        [
            make_event("quake", category=Category.DISASTER, point=Point(10, 50), country_iso="de"),
            make_event(
                "flight", category=Category.AVIATION, point=Point(-100, 40), country_iso="US"
            ),
            make_event("kev", category=Category.CYBER, point=None),
            make_event("old", published_at=NOW - timedelta(days=2), point=Point(179.5, 0)),
            make_event("fiji", point=Point(-179.5, 0), source_id="other"),
        ]
    )
    everything = store.query(EventQuery())
    assert len(everything) == 5
    assert everything[0].published_at >= everything[-1].published_at
    assert {e.subtype for e in store.query(EventQuery(categories=frozenset({Category.CYBER})))} == {
        "earthquake"
    }
    assert len(store.query(EventQuery(country_iso="de"))) == 1
    assert (
        len(store.query(EventQuery(country_iso="DE", categories=frozenset({Category.CYBER})))) == 0
    )
    europe = BoundingBox(west=0, south=40, east=20, north=60)
    assert [e.id for e in store.query(EventQuery(bbox=europe))] == [make_event("quake").id]
    dateline = BoundingBox(west=170, south=-10, east=-170, north=10)
    assert len(store.query(EventQuery(bbox=dateline))) == 2
    assert len(store.query(EventQuery(since=NOW - timedelta(hours=1)))) == 4
    assert len(store.query(EventQuery(source_ids=frozenset({"other"})))) == 1
    assert len(store.query(EventQuery(limit=2))) == 2


def test_prune_by_window_and_cap() -> None:
    budgets = {Category.DISASTER: RetentionBudget(timedelta(hours=1), 3)}
    store = InMemoryEventStore(budgets=budgets)
    events = [make_event(f"e{i}", observed_at=NOW - timedelta(minutes=10 * i)) for i in range(8)]
    store.upsert(events)
    result = store.prune(NOW)
    # e7 is 70 minutes old (expired); of the remaining 7 only the newest 3 survive the cap.
    assert result.expired == 1
    assert result.evicted == 4
    assert len(result.ids) == 5
    assert store.stats().total == 3
    survivors = {e.id for e in store.query(EventQuery())}
    assert survivors == {make_event(f"e{i}").id for i in range(3)}


def test_prune_by_memory_budget() -> None:
    sample = make_event("x")
    per_event = estimate_bytes(sample)
    store = InMemoryEventStore(memory_budget_bytes=per_event * 2 + 10)
    store.upsert([make_event(f"m{i}", observed_at=NOW + timedelta(seconds=i)) for i in range(5)])
    # The budget holds from the moment of insertion; the next prune announces the losses.
    assert store.stats().total == 2
    assert store.stats().estimated_bytes <= store.stats().budget_bytes
    result = store.prune(NOW)
    assert result.evicted == 3
    assert len(result.ids) == 3
    assert store.prune(NOW).ids == ()
    stats = store.stats()
    assert stats.total == 2
    assert stats.estimated_bytes <= stats.budget_bytes
    assert stats.per_category[0].category is Category.DISASTER
    assert stats.per_category[0].count == 2


def test_stats_empty_store() -> None:
    stats = InMemoryEventStore().stats()
    assert stats.total == 0
    assert stats.per_category == ()


def test_attributes_are_bounded_in_count_and_length() -> None:
    frozen = freeze_attributes({"long": "x" * 900, "n": 1, **{f"k{i}": i for i in range(60)}})
    assert len(frozen) == MAX_ATTRIBUTES
    assert len(str(frozen["long"])) == MAX_ATTRIBUTE_CHARS
    assert frozen["n"] == 1
