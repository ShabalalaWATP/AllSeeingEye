"""The adsb.lol list, emergency-squawk and watched-area connectors."""

from __future__ import annotations

import copy
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds.adsb import LADD, AdsbListConnector, flag_tags
from ase.adapters.feeds.adsb_watch import (
    AdsbAreaConnector,
    AdsbSquawkConnector,
    WatchArea,
    _area,
    load_watch_areas,
)
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.http_contracts import FeedRateLimitedError
from ase.adapters.feeds.registry import build_connectors
from feeds_helpers import NOW, FakeHttp, load_fixture
from helpers import FakeClock


def fixture() -> dict:
    return copy.deepcopy(load_fixture("adsb_mil.json"))


def usable(data: dict) -> list[dict]:
    """The records that carry a position, in feed order."""
    return [item for item in data["ac"] if "lat" in item and "lon" in item]


async def test_list_connectors_tag_by_list_and_database_flags() -> None:
    data = fixture()
    usable(data)[0]["dbFlags"] = 11  # military, interesting, LADD
    ladd = AdsbListConnector(
        FakeHttp({"ladd": data}),
        FakeClock(NOW),
        LADD,
        subtype="ladd_aircraft",
        tags=frozenset({"ladd"}),
    )
    events = await ladd.fetch()
    assert len(events) == 2 and events[0].source_id == "adsb_ladd"  # two records have positions
    assert all(event.subtype == "ladd_aircraft" for event in events)
    flagged = next(event for event in events if event.attributes["db_flags"] == 11)
    assert {"ladd", "military", "interesting", "adsb"} <= flagged.tags
    assert "nac_p" in flagged.attributes
    assert flag_tags({"dbFlags": 6}) == {"interesting", "pia"} and flag_tags({}) == set()


async def test_squawk_connector_grades_emergencies_and_dedupes() -> None:
    general = fixture()
    for item in general["ac"]:
        item["squawk"] = "7700"
    hijack = {"ac": [dict(general["ac"][0], squawk="7500")]}
    http = FakeHttp({"sqk/7700": general, "sqk/7600": {"ac": []}, "sqk/7500": hijack})
    events = await AdsbSquawkConnector(http, FakeClock(NOW)).fetch()
    assert len(events) == 2  # the hijack record is the same airframe as one of the 7700 ones
    first = events[0]
    assert first.subtype == "emergency" and first.severity == 0.95
    assert first.title.endswith("squawk 7500, unlawful interference")
    assert {"emergency", "squawk_7500"} <= first.tags
    assert events[1].severity == 0.8 and "squawk 7700" in events[1].title
    assert len(http.requests) == 3


class FlakyHttp(FakeHttp):
    async def get_json(self, url: str, *, conditional: bool = True) -> object:
        if "sqk/7600" in url:
            raise FeedFetchError("HTTP 503")
        return await super().get_json(url, conditional=conditional)


async def test_squawk_connector_survives_one_failed_code() -> None:
    http = FlakyHttp({"sqk/7700": fixture(), "sqk/7500": {"ac": []}})
    events = await AdsbSquawkConnector(http, FakeClock(NOW)).fetch()
    assert len(events) == 2


async def test_squawk_throttle_keeps_successful_aircraft_and_stops_batch() -> None:
    http = AsyncMock()
    http.get_json.side_effect = [fixture(), FeedRateLimitedError("https://private", None)]
    connector = AdsbSquawkConnector(http, FakeClock(NOW))
    assert len(await connector.fetch()) == 2
    assert http.get_json.await_count == 2
    assert "1/3 queries retrieved" in connector.warning
    http.get_json.side_effect = None
    http.get_json.return_value = {"ac": []}
    await connector.fetch()
    assert connector.warning is None
    assert http.get_json.await_args_list[2].args[0].endswith("/sqk/7600")


async def test_squawk_throttle_without_responses_preserves_backoff() -> None:
    http = AsyncMock()
    http.get_json.side_effect = FeedRateLimitedError(
        "https://private?secret=value", timedelta(seconds=90)
    )
    connector = AdsbSquawkConnector(http, FakeClock(NOW))
    with pytest.raises(FeedRateLimitedError) as caught:
        await connector.fetch()
    assert caught.value.retry_after == timedelta(seconds=90)
    assert "secret" not in str(caught.value)
    assert http.get_json.await_count == 1


async def test_area_connector_polls_every_watched_area_once() -> None:
    areas = load_watch_areas()
    assert len(areas) == 22 and all(area.radius_nm <= 250 for area in areas)
    assert areas[0].url == "https://api.adsb.lol/v2/point/45/33.5/250"
    data = fixture()
    first, second = usable(data)[:2]
    first["dbFlags"] = 1
    second.pop("dbFlags", None)
    http = FakeHttp({"v2/point": data})
    connector = AdsbAreaConnector(http, FakeClock(NOW), areas[:2])
    events = await connector.fetch()
    assert len(http.requests) == 2 and len(events) == 2  # the same airframes over both areas
    military = next(event for event in events if event.attributes["db_flags"] == 1)
    civil = next(event for event in events if event.attributes["db_flags"] != 1)
    assert military.subtype == "military_aircraft" and civil.subtype == "aircraft"
    assert "area_watch" in military.tags and f"area_{areas[0].id}" in military.tags
    assert connector.areas == areas[:2]
    with pytest.raises(ValueError, match="out of range"):
        _area({"id": "x", "lat": 95, "lon": 0})
    assert _area({"id": "y", "lat": 0, "lon": 0, "radius_nm": 999}).radius_nm == 250
    assert WatchArea("z", "Z", 1.5, -2.25, 100).url == "https://api.adsb.lol/v2/point/1.5/-2.25/100"


def test_registry_includes_the_aviation_connectors() -> None:
    ids = {connector.spec.id for connector in build_connectors(FakeHttp(), FakeClock(NOW))}
    assert {"adsb_mil", "adsb_ladd", "adsb_pia", "adsb_emergency", "adsb_areas"} <= ids
