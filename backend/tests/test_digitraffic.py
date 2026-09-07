"""AIS sentinel values, clocks, fresh positions and shared maritime retention."""

import asyncio
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest

from ase.adapters.feeds import digitraffic
from ase.adapters.feeds.digitraffic import DigitrafficConnector, parse_locations
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.store.memory import InMemoryEventStore
from ase.domain.events import Category
from feeds_helpers import FakeClock, FakeConnector, FakeHttp, make_event
from test_pipeline_and_scheduler import build_scheduler

NOW = datetime(2026, 9, 7, 12, tzinfo=UTC)


def feature(*, age=0, mmsi=230123456, coordinates=None, **fields):
    return {
        "type": "Feature",
        "mmsi": mmsi,
        "geometry": {"type": "Point", "coordinates": coordinates or [0, 0]},
        "properties": {
            "mmsi": mmsi,
            "sog": 10.2,
            "cog": 90.5,
            "heading": 92,
            "timestamp": 60,
            "timestampExternal": int((NOW - timedelta(seconds=age)).timestamp() * 1000),
            "navStat": 0,
            "posAcc": True,
            "raim": False,
            **fields,
        },
    }


def collection(*rows):
    return {"type": "FeatureCollection", "features": list(rows)}


def test_position_time_identity_units_and_unknown_values():
    event = parse_locations(collection(feature(mmsi=123456)), NOW)[0]
    assert event.attributes["mmsi"] == "000123456"
    assert event.published_at == event.observed_at == NOW
    assert event.attributes["ais_timestamp_code"] == 60
    assert event.attributes["track_deg"] == 92
    assert event.attributes["speed_over_ground_knots"] == 10.2
    assert event.point.lon == event.point.lat == 0
    assert event.category is Category.MARITIME and event.subtype == "vessel_position"
    unknown = parse_locations(collection(feature(heading=511, sog=102.3, cog=360)), NOW)[0]
    assert unknown.attributes["track_deg"] is None
    assert unknown.attributes["speed_over_ground_knots"] is None
    assert unknown.attributes["orientation_basis"] == "unknown"
    course = parse_locations(collection(feature(heading=511)), NOW)[0]
    assert course.attributes["track_deg"] == 90.5
    assert course.attributes["orientation_basis"] == "course"


@pytest.mark.parametrize(
    "change",
    [
        {"age": 901},
        {"age": -31},
        {"coordinates": [181, 91]},
        {"coordinates": [float("nan"), 0]},
    ],
)
def test_unusable_or_stale_positions_are_not_displayed(change):
    assert parse_locations(collection(feature(**change)), NOW) == []


@pytest.mark.parametrize(
    "change",
    [
        {"mmsi": True},
        {"mmsi": 0},
        {"mmsi": 1000000000},
        {"coordinates": [True, 0]},
        {"timestampExternal": "invalid"},
        {"timestampExternal": 10**30},
        {"navStat": 16},
        {"timestamp": 64},
    ],
)
def test_malformed_records_fail_safely(change):
    with pytest.raises(FeedFetchError):
        parse_locations(collection(feature(**change)), NOW)


def test_collection_limits_and_mmsi_mismatch(monkeypatch):

    monkeypatch.setattr(digitraffic, "MAX_RECORDS", 1)
    with pytest.raises(FeedFetchError):
        parse_locations(collection(feature(), feature()), NOW)
    bad = feature()
    bad["properties"]["mmsi"] += 1
    with pytest.raises(FeedFetchError):
        parse_locations(collection(bad), NOW)
    for data in ([], {}, collection(None), {"type": "FeatureCollection", "features": {}}):
        with pytest.raises(FeedFetchError):
            parse_locations(data, NOW)


def test_latest_duplicate_wins_and_stationary_fresh_updates_refresh_hash():
    old = parse_locations(collection(feature(age=120)), NOW)[0]
    new = parse_locations(collection(feature(), feature(age=120)), NOW)[0]
    assert old.id == new.id and old.content_hash != new.content_hash
    store = InMemoryEventStore()
    store.upsert([old])
    assert store.upsert([new]).updated == 1
    assert store.get(old.id).published_at == NOW


def test_vessels_expire_from_record_time_even_after_fresh_download_without_expiring_warnings():
    vessel = parse_locations(collection(feature(age=900)), NOW)[0]
    warning = make_event("warning", category=Category.MARITIME).with_changes(observed_at=NOW)
    store = InMemoryEventStore()
    store.upsert([vessel, warning])
    assert store.prune(NOW).expired == 0
    result = store.prune(NOW + timedelta(seconds=1))
    assert result.ids == (vessel.id,) and result.expired == 1
    assert store.get(warning.id) == warning
    assert store.get(vessel.id) is None


async def test_bounded_query_and_connector_contract():

    class Http:
        async def get_json(self, url, **kwargs):
            query = parse_qs(urlsplit(url).query)
            assert int(query["to"][0]) - int(query["from"][0]) == 900000
            assert kwargs == {"conditional": False, "max_redirects": 0}
            return collection(feature())

    connector = DigitrafficConnector(Http(), FakeClock(NOW))
    assert (await connector.fetch())[0].source_id == "digitraffic_ais"


def test_registry_uses_dedicated_transport_and_honours_disable():
    http = FakeHttp()
    connectors = build_connectors(http, FakeClock(NOW), digitraffic_http=http)
    assert sum(connector.spec.id == "digitraffic_ais" for connector in connectors) == 1
    assert all(
        connector.spec.id != "digitraffic_ais"
        for connector in build_connectors(
            http,
            FakeClock(NOW),
            disabled=["digitraffic_ais"],
            digitraffic_http=http,
        )
    )


async def test_feed_outage_expires_vessel_and_publishes_expiry():
    vessel = parse_locations(collection(feature(age=890)), NOW)[0]
    connector = FakeConnector(events=[])
    connector.failures = 1
    clock = FakeClock(NOW)
    scheduler, store, bus, _ = build_scheduler([], clock)
    store.upsert([vessel])
    assert not (await scheduler.poll_once(connector)).ok
    assert store.get(vessel.id) is not None
    subscription = bus.subscribe()
    await scheduler.start()
    for _ in range(12):
        await asyncio.sleep(0)
    await scheduler.stop()
    subscription.close()
    messages = [message async for message in subscription]
    assert any(
        message.kind == "event.expire" and vessel.id in str(message.payload) for message in messages
    )
    assert store.get(vessel.id) is None
