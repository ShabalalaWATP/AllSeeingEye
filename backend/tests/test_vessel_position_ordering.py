"""Delayed AIS batches must not regress a retained position or its expiry time."""

from datetime import timedelta

import pytest

from ase.adapters.feeds.aisstream_positions import parse_position
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.feeds import EventQuery
from ase.domain.events import Category, Point
from feeds_helpers import NOW, make_event


@pytest.mark.parametrize("cooperative", [False, True])
async def test_delayed_ais_batch_preserves_fresh_position_and_original_expiry(cooperative):
    def report(recorded, received, latitude):
        return parse_position(
            {
                "MessageType": "PositionReport",
                "MetaData": {"MMSI": 235123456, "time_utc": recorded.isoformat()},
                "Message": {
                    "PositionReport": {
                        "UserID": 235123456,
                        "Valid": True,
                        "Latitude": latitude,
                        "Longitude": 1.5,
                    }
                },
            },
            received,
        )

    current = report(NOW, NOW, 51.1)
    delayed = report(NOW - timedelta(minutes=13), NOW + timedelta(seconds=70), 51.0)
    assert current is not None and delayed is not None
    store = InMemoryEventStore()
    store.upsert([current])
    result = await store.upsert_cooperatively([delayed]) if cooperative else store.upsert([delayed])
    assert (result.updated, result.unchanged, result.changed_ids) == (0, 1, ())
    assert store.get(current.id) is current
    assert store.query(EventQuery(categories=frozenset({Category.MARITIME}))) == [current]
    assert store.prune(NOW + timedelta(minutes=3)).ids == ()
    assert store.prune(NOW + timedelta(minutes=15)).ids == ()
    assert store.prune(NOW + timedelta(minutes=15, seconds=1)).ids == (current.id,)


@pytest.mark.parametrize("seconds", [0, 1])
def test_equal_or_newer_vessel_timestamp_can_update_position_and_metadata(seconds):
    store = InMemoryEventStore()
    original = make_event(category=Category.MARITIME, subtype="vessel_position")
    updated = original.with_changes(
        published_at=NOW + timedelta(seconds=seconds),
        observed_at=NOW + timedelta(seconds=70),
        point=Point(lon=1.5, lat=51.1),
        title="Updated vessel name",
        content_hash="updated-vessel",
    )
    store.upsert([original])
    result = store.upsert([updated])
    assert (result.updated, result.unchanged, result.changed_ids) == (1, 0, (original.id,))
    assert store.get(original.id) is updated


@pytest.mark.parametrize(
    "existing_category,existing_subtype,incoming_category,incoming_subtype",
    [
        (Category.MARITIME, "incident", Category.MARITIME, "incident"),
        (Category.MARITIME, "incident", Category.MARITIME, "vessel_position"),
        (Category.MARITIME, "vessel_position", Category.MARITIME, "incident"),
        (Category.NEWS, "vessel_position", Category.MARITIME, "vessel_position"),
        (Category.MARITIME, "vessel_position", Category.NEWS, "vessel_position"),
        (Category.AVIATION, "aircraft", Category.AVIATION, "aircraft"),
    ],
)
def test_non_position_revisions_keep_existing_update_semantics(
    existing_category, existing_subtype, incoming_category, incoming_subtype
):
    original = make_event(category=existing_category, subtype=existing_subtype)
    revision = original.with_changes(
        category=incoming_category,
        subtype=incoming_subtype,
        published_at=NOW - timedelta(minutes=1),
        content_hash="revised",
    )
    store = InMemoryEventStore()
    store.upsert([original])
    assert store.upsert([revision]).updated == 1
    assert store.get(original.id) is revision


@pytest.mark.parametrize("missing", ["existing", "incoming"])
def test_missing_position_time_keeps_existing_update_semantics(missing):
    original = make_event(category=Category.MARITIME, subtype="vessel_position")
    revision = original.with_changes(content_hash="revised")
    if missing == "existing":
        original = original.with_changes(published_at=None)
    else:
        revision = revision.with_changes(published_at=None)
    store = InMemoryEventStore()
    store.upsert([original])
    assert store.upsert([revision]).updated == 1
    assert store.get(original.id) is revision
