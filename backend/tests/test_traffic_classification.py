"""Provider classifications survive overlap without guessing from identity strings."""

from datetime import timedelta

import pytest

from ase.adapters.feeds.adsb import AdsbMilitaryConnector, aircraft_event, records
from ase.adapters.feeds.adsb_classification import AircraftClassificationCache
from ase.adapters.feeds.adsb_watch import AREAS, AdsbAreaConnector, WatchArea
from ase.adapters.feeds.aisstream import AisStreamConnector
from ase.adapters.feeds.aisstream_classification import VesselClassificationCache, static_record
from ase.adapters.feeds.aisstream_positions import parse_position
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.ports.feeds import EventQuery
from ase.domain.events import Category
from ase.domain.traffic_classification import is_reported_military
from feeds_helpers import NOW, FakeClock, FakeHttp, make_event
from test_aisstream import message, setup


def aircraft(**changes):
    return {"hex": "abc123", "lat": 51, "lon": 0, "seen_pos": 1, "flight": "NAVY01", **changes}


async def test_shared_classification_survives_area_overwrite_then_expires():
    cache = AircraftClassificationCache()
    clock = FakeClock(NOW)
    http = FakeHttp({"/mil": {"ac": [aircraft()]}, "/point": {"ac": [aircraft(lon=1)]}})
    mil = await AdsbMilitaryConnector(http, clock, classifications=cache).fetch()
    area = AdsbAreaConnector(
        http, clock, [WatchArea("uk", "UK", 51, 0, 250)], classifications=cache
    )
    current = (await area.fetch())[0]
    assert current.id == mil[0].id and current.source_id == "adsb_areas"
    assert current.attributes["military"] is True and "military" in current.tags
    assert current.attributes["military_classification_basis"] == "adsb_lol_military_list"
    store = InMemoryEventStore()
    store.upsert(mil)
    store.upsert([current])
    assert len(store.query(EventQuery(military=True))) == 1
    clock.advance(timedelta(hours=25))
    assert "military" not in (await area.fetch())[0].tags


def test_name_alone_is_not_military_and_bad_numbers_do_not_crash():
    event = aircraft_event(
        AREAS,
        aircraft(dbFlags=float("nan"), alt_baro=float("inf")),
        NOW,
        subtype="aircraft",
        tags=frozenset(),
    )
    assert event and "military" not in event.tags and event.attributes["military"] is False
    assert records({"ac": None}) == []


def test_late_area_response_cannot_move_aircraft_backwards_but_grading_put_is_unchanged():
    newer = aircraft_event(
        AREAS, aircraft(lon=2, seen_pos=1), NOW, subtype="aircraft", tags=frozenset()
    )
    older = aircraft_event(
        AREAS, aircraft(lon=1, seen_pos=20), NOW, subtype="aircraft", tags=frozenset()
    )
    store = InMemoryEventStore()
    store.upsert([newer])
    assert store.upsert([older]).unchanged == 1
    assert store.get(newer.id).point.lon == 2
    graded = newer.with_changes(grade_rationale="Reviewed transponder record")
    store.put([graded])
    assert store.get(newer.id).grade_rationale == graded.grade_rationale


def test_fresh_stationary_report_refreshes_without_inventing_replayed_freshness():
    first = aircraft_event(AREAS, aircraft(seen_pos=1), NOW, subtype="aircraft", tags=frozenset())
    later = NOW + timedelta(minutes=2)
    fresh = aircraft_event(AREAS, aircraft(seen_pos=1), later, subtype="aircraft", tags=frozenset())
    replay = aircraft_event(
        AREAS, aircraft(seen_pos=121), later, subtype="aircraft", tags=frozenset()
    )
    assert first.content_hash == replay.content_hash
    assert first.content_hash != fresh.content_hash
    store = InMemoryEventStore()
    store.upsert([first])
    assert store.upsert([replay]).unchanged == 1
    assert store.upsert([fresh]).updated == 1
    assert store.get(first.id).observed_at == later


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("MetaData", "MMSI", "bad"),
        ("ShipStaticData", "UserID", 1),
        ("MetaData", "time_utc", 1),
        ("MetaData", "time_utc", "2026-09-05"),
    ],
)
def test_invalid_static_identity_or_timestamp_is_rejected(section, field, value):
    data = static()
    target = data["MetaData"] if section == "MetaData" else data["Message"][section]
    target[field] = value
    assert static_record(data, NOW) is None


def test_invalid_part_b_does_not_classify():
    data = static(kind="StaticDataReport")
    data["Message"]["StaticDataReport"]["ReportB"]["Valid"] = False
    assert static_record(data, NOW) is None


def test_classification_cache_is_bounded(monkeypatch):
    monkeypatch.setattr("ase.adapters.feeds.adsb_classification.MAX_CLASSIFICATIONS", 2)
    cache = AircraftClassificationCache()
    events = [
        aircraft_event(
            AREAS, aircraft(hex=f"abc12{i}", dbFlags=1), NOW, subtype="aircraft", tags=frozenset()
        )
        for i in range(3)
    ]
    for event in events:
        cache.enrich(event, NOW)
    unlabelled = events[0].with_changes(tags=frozenset(), attributes={})
    assert "military" not in cache.enrich(unlabelled, NOW).tags


async def test_area_total_cap_rotates_regions_instead_of_permanent_starvation(monkeypatch):
    monkeypatch.setattr("ase.adapters.feeds.adsb_watch.MAX_AREA_EVENTS", 1)
    areas = [WatchArea("a", "A", 1, 0, 250), WatchArea("b", "B", 2, 0, 250)]
    http = FakeHttp(
        {
            "/point/1/": {"ac": [aircraft(hex="aaaaaa")]},
            "/point/2/": {"ac": [aircraft(hex="bbbbbb")]},
        }
    )
    connector = AdsbAreaConnector(http, FakeClock(NOW), areas)
    first, second = await connector.fetch(), await connector.fetch()
    assert len(first) == len(second) == 1
    assert first[0].id != second[0].id


def static(ship_type=35, *, kind="ShipStaticData", recorded=NOW):
    fields = {"UserID": 235123456, "Valid": True, "Type": ship_type}
    if kind == "StaticDataReport":
        fields = {
            "UserID": 235123456,
            "Valid": True,
            "ReportB": {"Valid": True, "ShipType": ship_type},
        }
    return {
        "MessageType": kind,
        "MetaData": {"MMSI": 235123456, "time_utc": recorded.isoformat()},
        "Message": {kind: fields},
    }


@pytest.mark.parametrize("kind", ["ShipStaticData", "StaticDataReport"])
def test_static_military_operations_explicitly_labels_fresh_positions(kind):
    cache = VesselClassificationCache()
    cache.observe(static(kind=kind), NOW)
    position = parse_position(message(), NOW)
    event = cache.enrich(position, NOW)
    assert event.point == position.point and event.published_at == position.published_at
    assert event.attributes["military"] is True
    assert event.attributes["ship_type_code"] == 35
    assert event.attributes["military_classification_basis"] == "reported_ais_ship_type_35"
    assert event.tags >= {"military"} and event.content_hash != position.content_hash
    assert parse_position(static(kind=kind), NOW) is None


def test_law_enforcement_and_names_are_not_naval_and_newer_type_can_clear():
    cache = VesselClassificationCache()
    position = parse_position(message(), NOW)
    assert "military" not in cache.enrich(position.with_changes(title="HMS MOCK"), NOW).tags
    cache.observe(static(), NOW)
    cache.observe(static(55, recorded=NOW + timedelta(seconds=1)), NOW)
    event = cache.enrich(position, NOW)
    assert event.attributes["ship_type_code"] == 55
    assert event.attributes["military"] is False and "military" not in event.tags
    cache.observe(static(35, recorded=NOW - timedelta(seconds=1)), NOW)
    assert cache.enrich(position, NOW).attributes["ship_type_code"] == 55


def test_static_cache_expires_and_is_bounded(monkeypatch):
    cache = VesselClassificationCache()
    position = parse_position(message(), NOW)
    cache.observe(static(), NOW)
    assert cache.enrich(position, NOW + timedelta(hours=7)) == position
    monkeypatch.setattr("ase.adapters.feeds.aisstream_classification.MAX_STATIC_RECORDS", 1)
    cache.observe(static(), NOW)
    other = static()
    other["MetaData"]["MMSI"] = other["Message"]["ShipStaticData"]["UserID"] = 235123457
    cache.observe(other, NOW)
    assert cache.enrich(position, NOW) == position


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"MessageType": []},
        {"MessageType": "ShipStaticData"},
        static(0),
        static(True),
        static(100),
        static(recorded=NOW - timedelta(hours=7)),
        static(recorded=NOW + timedelta(minutes=1)),
    ],
)
def test_invalid_static_record_does_not_classify(data):
    assert static_record(data, NOW) is None


async def test_stream_subscribes_static_types_and_enriches_late_metadata(monkeypatch):

    socket, _ = setup(monkeypatch, [message(), static()])
    connector = AisStreamConnector("fixture", FakeClock(NOW))
    events = await connector.fetch()
    assert events[0].attributes["military"] is True
    assert {"ShipStaticData", "StaticDataReport"} <= set(socket.sent[0]["FilterMessageTypes"])
    setup(monkeypatch, [message()])
    assert (await connector.fetch())[0].attributes["military"] is True


def test_military_query_filters_before_limit_and_pagination_is_stable():
    store = InMemoryEventStore()
    military = make_event(
        "mil", category=Category.AVIATION, published_at=NOW - timedelta(minutes=1)
    ).with_changes(tags=frozenset({"military"}))
    store.upsert(
        [military, *[make_event(f"civil{i}", category=Category.AVIATION) for i in range(20)]]
    )
    assert store.query(
        EventQuery(categories=frozenset({Category.AVIATION}), military=True, limit=1)
    ) == [military]
    first = store.query(EventQuery(military=False, limit=10))
    second = store.query(EventQuery(military=False, limit=10, offset=10))
    assert len(first) == len(second) == 10
    assert not {event.id for event in first} & {event.id for event in second}
    assert first == store.query(EventQuery(military=False, limit=10))


def test_legacy_explicit_types_are_military_but_nontraffic_and_names_are_not():
    aircraft = make_event(category=Category.AVIATION, subtype="military_aircraft")
    vessel = make_event(category=Category.MARITIME).with_changes(attributes={"ship_type_code": 35})
    assert is_reported_military(aircraft) and is_reported_military(vessel)
    assert not is_reported_military(
        make_event(category=Category.CONFLICT).with_changes(tags={"military"})
    )
    assert not is_reported_military(make_event(category=Category.MARITIME, title="HMS MOCK"))
