"""Whole-Earth query geometry, bounded rotation and temporary viewport interests."""

import math
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds.adsb_global import AdsbGlobalConnector, global_areas
from ase.adapters.feeds.adsb_viewport import AdsbViewportConnector, AircraftInterestQueue
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.registry import build_connectors
from feeds_helpers import NOW, FakeClock, FakeHttp


def distance_nm(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    angle = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 3440.065 * 2 * math.asin(math.sqrt(min(1, angle)))


def test_grid_covers_every_band_corner_and_interleaves_hemispheres():
    areas = global_areas()
    assert 1600 < len(areas) < 2000
    assert len({a.id for a in areas}) == len(areas)
    for area in areas:
        columns = math.ceil(72 * math.cos(math.radians(max(0, abs(area.lat) - 2.5))))
        for lat in (area.lat - 2.5, area.lat + 2.5):
            assert distance_nm(area.lat, area.lon, lat, area.lon + 180 / columns) < 250
    first = areas[:24]
    assert any(a.lat < -50 for a in first) and any(a.lat > 50 for a in first)
    assert any(a.lon < -90 for a in first) and any(a.lon > 90 for a in first)


async def test_sweep_queries_are_bounded_and_resume_without_duplicate_cells():
    http = AsyncMock()
    http.get_json.return_value = {"ac": [{"hex": "abcdef", "lat": 1, "lon": 2, "seen_pos": 3}]}
    connector = AdsbGlobalConnector(http, FakeClock(NOW))
    connector._request_interval = 0
    first = await connector.fetch()
    assert http.get_json.await_count == 24 and len(first) == 1
    assert first[0].published_at == NOW - timedelta(seconds=3)
    assert first[0].attributes["simultaneous_global_coverage"] is False
    assert "24/" in connector.coverage_warning
    assert connector.warning is None
    await connector.fetch()
    urls = [call.args[0] for call in http.get_json.await_args_list]
    assert len(urls) == len(set(urls)) == 48
    assert "48/" in connector.coverage_warning


async def test_interests_are_bounded_expire_and_rotate_without_renewing():
    clock = FakeClock(NOW)
    queue = AircraftInterestQueue(clock)
    for i in range(40):
        queue.request(i, i)
    first = queue.take()
    assert len(first) == 4 and first[0].lat == 8
    assert queue.take()[0].lat == 12
    clock.advance(timedelta(minutes=6))
    assert queue.take() == ()
    for latitude, longitude in [(91, 0), (0, 181), (math.nan, 0)]:
        with pytest.raises(ValueError):
            queue.request(latitude, longitude)
    http = AsyncMock()
    assert await AdsbViewportConnector(http, clock, queue).fetch() == []
    http.get_json.assert_not_awaited()


def test_registry_adds_global_and_only_wires_viewport_with_shared_queue():
    clock = FakeClock(NOW)
    base = build_connectors(FakeHttp(), clock)
    assert "adsb_global" in {c.spec.id for c in base}
    assert "adsb_viewport" not in {c.spec.id for c in base}
    selected = build_connectors(FakeHttp(), clock, aircraft_interests=AircraftInterestQueue(clock))
    assert "adsb_viewport" in {c.spec.id for c in selected}


async def test_viewport_connector_fetches_only_active_requested_circles():
    clock = FakeClock(NOW)
    queue = AircraftInterestQueue(clock)
    queue.request(-33.9, 151.2)
    http = AsyncMock()
    http.get_json.return_value = {"ac": []}
    connector = AdsbViewportConnector(http, clock, queue)
    connector._request_interval = 0
    assert await connector.fetch() == []
    http.get_json.assert_awaited_once_with(
        "https://api.adsb.lol/v2/point/-34/151/250", conditional=False
    )


async def test_failed_global_attempts_advance_to_new_cells():
    http = AsyncMock()
    http.get_json.side_effect = FeedFetchError("temporarily unavailable")
    connector = AdsbGlobalConnector(http, FakeClock(NOW))
    connector._request_interval = 0
    with pytest.raises(FeedFetchError):
        await connector.fetch()
    assert connector._attempted_total == 24
    http.get_json.side_effect = None
    http.get_json.return_value = {"ac": []}
    await connector.fetch()
    assert connector._attempted_total == 48


def test_registry_wires_both_firms_sensors_and_respects_family_and_individual_disables():
    def ids(**kwargs):
        return {c.spec.id for c in build_connectors(FakeHttp(), FakeClock(NOW), **kwargs)}

    assert {"firms_viirs_noaa20", "firms_viirs_noaa21"} <= ids(firms_key="development-test-key")
    assert "firms_viirs_noaa21" not in ids(
        firms_key="development-test-key", disabled=["firms_viirs_noaa21"]
    )
    assert not {"firms_viirs_noaa20", "firms_viirs_noaa21"} & ids(
        firms_key="development-test-key", disabled=["firms_viirs_noaa20"]
    )

    assert {"firms_public_noaa20", "firms_public_noaa21"} <= ids()
    assert not {"firms_public_noaa20", "firms_public_noaa21"} & ids(
        disabled=["firms_public_noaa20"]
    )
