"""Repeated NASA sensor polls cannot consume the whole shared event store."""

from datetime import timedelta

from ase.adapters.store.firms_retention import MAX_RETAINED_PER_SENSOR
from ase.adapters.store.memory import InMemoryEventStore, estimate_bytes
from ase.application.ports.feeds import EventQuery
from ase.domain.events import Category, Point
from feeds_helpers import NOW, make_event


def detection(index, source="firms_viirs_noaa20", *, remote=False):
    return make_event(
        f"{source}-{index}",
        source_id=source,
        subtype="thermal_detection",
        published_at=NOW + timedelta(seconds=index),
        observed_at=NOW,
        point=Point(150, -60) if remote else Point(0, 0),
    )


def test_cumulative_public_and_keyed_polls_share_cap_before_global_memory_eviction():
    plane = make_event("plane", category=Category.AVIATION, observed_at=NOW - timedelta(minutes=1))
    sensor = detection(99_999, "firms_public_noaa20")
    # Enough for the capped sensor and an older aircraft, but not two full polls.
    budget = estimate_bytes(sensor) * (MAX_RETAINED_PER_SENSOR + 100)
    store = InMemoryEventStore(memory_budget_bytes=budget)
    store.upsert([plane, detection(-1, remote=True)])
    store.upsert(detection(i) for i in range(15_000))
    store.upsert(detection(i, "firms_public_noaa20") for i in range(15_000, 30_000))
    items = store.query(
        EventQuery(
            source_ids=frozenset({"firms_viirs_noaa20", "firms_public_noaa20"}), limit=50_000
        )
    )
    assert len(items) == MAX_RETAINED_PER_SENSOR
    assert any(event.point.lat == -60 for event in items)
    assert store.get(plane.id) is not None
    assert store.stats().estimated_bytes <= budget
    expired = store.prune(NOW)
    assert expired.evicted == 20_001
    assert expired.resync_required
    assert all(store.get(identifier) is None for identifier in expired.ids)


def test_two_sensor_caps_and_put_updates_keep_source_indexes_consistent():
    store = InMemoryEventStore()
    for suffix in ("noaa20", "noaa21"):
        source = f"firms_viirs_{suffix}"
        store.put(detection(i, source) for i in range(10_002))
        assert len(store.query(EventQuery(source_ids=frozenset({source}), limit=50_000))) == 10_000
    assert store.stats().total == 20_000
    existing = store.query(EventQuery(source_ids=frozenset({"firms_viirs_noaa20"}), limit=1))[0]
    store.put([existing.with_changes(source_id="firms_public_noaa20")])
    assert store.query(EventQuery(source_ids=frozenset({"firms_public_noaa20"}))) == [
        store.get(existing.id)
    ]
    assert (
        len(store.query(EventQuery(source_ids=frozenset({"firms_viirs_noaa20"}), limit=50_000)))
        == 9_999
    )


def test_immediately_evicted_old_record_is_not_published_as_changed():
    store = InMemoryEventStore()
    store.upsert(detection(i) for i in range(10_000))
    old = detection(-2)
    result = store.upsert([old])
    assert store.get(old.id) is None
    assert old.id not in result.changed_ids
    assert old.id in store.prune(NOW).ids
