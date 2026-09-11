"""Documented snapshot fields, conservative validation and shared vessel retention."""

from datetime import timedelta

import pytest

from ase.adapters.feeds import barentswatch_positions
from ase.adapters.feeds.barentswatch import SPEC
from ase.adapters.feeds.barentswatch_positions import parse_positions
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.store.memory import InMemoryEventStore
from ase.domain.events import Category, Reliability
from ase.domain.source_discovery import source_coverage
from barentswatch_helpers import vessel
from feeds_helpers import NOW


def test_documented_snapshot_preserves_units_origin_and_regional_limits():
    event = parse_positions([vessel(mmsi=123456, name=" <b>TEST</b> ")], NOW)[0]
    assert event.attributes["mmsi"] == "000123456"
    assert event.title == "TEST"
    assert event.published_at == event.observed_at == NOW
    assert event.category is Category.MARITIME and event.subtype == "vessel_position"
    assert event.point.lon == 5.819193 and event.point.lat == 59.141722
    assert event.attributes["speed_over_ground_knots"] == 0.1
    assert event.attributes["track_deg"] == 63.8
    assert event.attributes["orientation_basis"] == "course"
    assert event.attributes["delivery_credit"] == "Data delivered by BarentsWatch"
    assert event.attributes["licence"] == "NLOD"
    assert event.reliability is Reliability.F
    assert SPEC.rating.status == "unassessed"
    assert SPEC.rating.assessed_grade is None
    assert "Svalbard" in event.summary and "Jan Mayen" in event.summary
    assert "15 metres" in event.summary and "45 metres" in event.summary
    assert source_coverage(SPEC.id).scope == "regional"
    assert source_coverage(SPEC.id).countries == ("NO", "SJ")


@pytest.mark.parametrize(
    "row",
    [
        None,
        [],
        {},
        vessel(mmsi=True),
        vessel(mmsi=0),
        vessel(mmsi=10**9),
        vessel(mmsi="257789800"),
        vessel(latitude=True),
        vessel(longitude="5.1"),
        vessel(latitude=91),
        vessel(longitude=181),
        vessel(latitude=float("nan")),
        vessel(longitude=float("inf")),
        vessel(age=901),
        vessel(age=-31),
        vessel(msgtime=None),
        vessel(msgtime="bad"),
        vessel(msgtime="x" * 65),
        vessel(msgtime="2026-09-05T00:00:00"),
        vessel(msgtime=True),
    ],
)
def test_malformed_stale_or_unavailable_records_are_skipped_individually(row):
    events = parse_positions([row, vessel()], NOW)
    assert len(events) == 1
    assert events[0].attributes["mmsi"] == "257789800"


@pytest.mark.parametrize("value", [True, "10", None, -1, float("nan"), float("inf"), 10**400])
def test_invalid_optional_numbers_do_not_become_measurements(value):
    event = parse_positions(
        [vessel(trueHeading=value, courseOverGround=value, speedOverGround=value)], NOW
    )[0]
    assert event.attributes["track_deg"] is None
    assert event.attributes["speed_over_ground_knots"] is None
    assert event.attributes["orientation_basis"] == "unknown"


def test_heading_precedence_zero_coordinates_and_ais_sentinels():
    event = parse_positions([vessel(trueHeading=92, latitude=0, longitude=0)], NOW)[0]
    assert event.attributes["track_deg"] == 92
    assert event.attributes["orientation_basis"] == "heading"
    assert event.point.lat == event.point.lon == 0
    unknown = parse_positions(
        [vessel(trueHeading=511, courseOverGround=360, speedOverGround=102.3, name=None)], NOW
    )[0]
    assert unknown.attributes["track_deg"] is None
    assert unknown.attributes["speed_over_ground_knots"] is None
    assert unknown.title == "AIS vessel 257789800"


@pytest.mark.parametrize("ship_type", [None, True, "35", 0, 100, 55, 35, 70])
def test_only_reported_type_35_has_military_classification(ship_type):
    event = parse_positions([vessel(shipType=ship_type, name="NAVY WARSHIP")], NOW)[0]
    military = type(ship_type) is int and ship_type == 35
    assert event.attributes["military"] is military
    assert ("military" in event.tags) is military
    assert event.attributes["military_classification_basis"] == (
        "reported_ais_ship_type_35" if military else None
    )
    assert event.attributes["ship_type_timestamp_kind"] == "static_message_time_unavailable"
    assert "ship_type_observed_at" not in event.attributes
    if ship_type == 55:
        assert event.attributes["ship_type_label"] == "Reported law enforcement"


def test_latest_record_per_mmsi_wins_without_extending_stale_positions():
    events = parse_positions([vessel(age=20), vessel(), vessel(age=40)], NOW)
    assert len(events) == 1 and events[0].published_at == NOW
    older = parse_positions([vessel(age=900)], NOW)[0]
    assert older.id == events[0].id and older.content_hash != events[0].content_hash
    store = InMemoryEventStore()
    store.upsert([older])
    assert store.prune(NOW + timedelta(seconds=1)).expired == 1
    store.upsert([older])
    assert store.upsert(events).updated == 1
    assert store.get(events[0].id).published_at == NOW


def test_static_name_correction_updates_stored_event_with_same_position_and_time():
    original = parse_positions([vessel(name="OLD NAME")], NOW)[0]
    corrected = parse_positions([vessel(name="CORRECTED NAME")], NOW)[0]
    assert original.id == corrected.id and original.content_hash != corrected.content_hash
    store = InMemoryEventStore()
    store.upsert([original])
    assert store.upsert([corrected]).updated == 1
    assert store.get(original.id).title == "CORRECTED NAME"
    assert store.get(original.id).attributes["ship_name"] == "CORRECTED NAME"


@pytest.mark.parametrize("value", [None, True, "1", -1, 15, 16, 0, 14])
def test_navigation_status_retains_reported_codes_and_rejects_unavailable(value):
    event = parse_positions([vessel(navigationalStatus=value)], NOW)[0]
    expected = value if type(value) is int and 0 <= value < 15 else None
    assert event.attributes["navigation_status_code"] == expected


@pytest.mark.parametrize("data", [{}, None, "secret-invalid-body", [vessel(), vessel()]])
def test_invalid_or_oversized_collections_fail_with_safe_errors(data, monkeypatch):
    monkeypatch.setattr(barentswatch_positions, "MAX_RECORDS", 1)
    with pytest.raises(FeedFetchError, match="invalid or exceeds") as error:
        parse_positions(data, NOW)
    assert "secret" not in str(error.value)
    assert parse_positions([], NOW) == []
