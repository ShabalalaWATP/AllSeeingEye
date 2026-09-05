"""Each connector turns its recorded upstream payload into well-formed events."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ase.adapters.feeds.cisa_kev import CisaKevConnector
from ase.adapters.feeds.eonet import EonetConnector
from ase.adapters.feeds.gdacs import GdacsConnector
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.feeds.swpc import SwpcAlertsConnector, SwpcScalesConnector, headline
from ase.adapters.feeds.usgs import UsgsConnector
from ase.domain.events import Category, Credibility, GeoConfidence
from feeds_helpers import NOW, FakeClock, FakeHttp, load_fixture


async def test_usgs_connector() -> None:
    http = FakeHttp({"all_day.geojson": load_fixture("usgs_all_hour.geojson")})
    events = await UsgsConnector(http, FakeClock(NOW)).fetch()  # type: ignore[arg-type]
    assert len(events) == 5
    quake = events[0]
    assert quake.category is Category.DISASTER and quake.subtype == "earthquake"
    assert quake.title.startswith("M") and quake.point is not None
    assert quake.geo_confidence is GeoConfidence.EXACT
    assert quake.attributes["magnitude"] == 2.5
    assert quake.attributes["depth_km"] is not None
    assert quake.credibility in (Credibility.CONFIRMED, Credibility.PROBABLY_TRUE)
    assert quake.published_at.tzinfo is UTC
    assert 0 < (quake.severity or 0) < 1
    assert len({e.id for e in events}) == 5
    assert await UsgsConnector(FakeHttp(not_modified=True), FakeClock(NOW)).fetch() == []  # type: ignore[arg-type]
    broken = {"features": [{"id": "x", "properties": {}, "geometry": {"coordinates": []}}]}
    assert await UsgsConnector(FakeHttp({"all_day": broken}), FakeClock(NOW)).fetch() == []  # type: ignore[arg-type]


async def test_eonet_connector() -> None:
    http = FakeHttp({"eonet.gsfc.nasa.gov": load_fixture("eonet_events.json")})
    events = await EonetConnector(http, FakeClock(NOW)).fetch()  # type: ignore[arg-type]
    assert events
    fire = events[0]
    assert fire.subtype == "wildfires"
    assert fire.point is not None and fire.url is not None
    assert fire.attributes["eonet_category"] == "Wildfires"
    assert fire.severity is not None
    polygon = {
        "events": [
            {
                "id": "EONET_P",
                "title": "Storm",
                "categories": [{"id": "severeStorms", "title": "Severe Storms"}],
                "sources": [],
                "link": "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_P",
                "geometry": [
                    {
                        "date": "2026-09-01T00:00:00Z",
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]],
                    }
                ],
            },
            {"id": "EONET_NOGEOM", "title": "x", "geometry": []},
        ]
    }
    events = await EonetConnector(FakeHttp({"eonet": polygon}), FakeClock(NOW)).fetch()  # type: ignore[arg-type]
    assert len(events) == 1
    assert events[0].subtype == "severe_storms"
    assert events[0].point is not None and abs(events[0].point.lon - 0.8) < 0.01


async def test_swpc_connectors() -> None:
    http = FakeHttp(
        {
            "alerts.json": load_fixture("swpc_alerts.json"),
            "noaa-scales.json": load_fixture("swpc_scales.json"),
        }
    )
    alerts = await SwpcAlertsConnector(http, FakeClock(NOW)).fetch()  # type: ignore[arg-type]
    assert len(alerts) == 4
    assert alerts[0].category is Category.SPACE
    assert alerts[0].point is None
    assert alerts[0].published_at.year == 2026
    assert alerts[0].attributes["product_id"]
    scales = await SwpcScalesConnector(http, FakeClock(NOW)).fetch()  # type: ignore[arg-type]
    assert len(scales) == 1
    assert scales[0].title.startswith("Space weather now: R")
    assert scales[0].severity is not None
    assert headline(
        "Space Weather Message Code: X\r\nIssue Time: now\r\n\r\nALERT: K-index of 5"
    ) == ("ALERT: K-index of 5")
    assert headline("nothing here") is None
    empty = await SwpcScalesConnector(FakeHttp({"noaa-scales.json": {}}), FakeClock(NOW)).fetch()  # type: ignore[arg-type]
    assert empty == []


async def test_cisa_kev_connector() -> None:
    fixture = load_fixture("cisa_kev.json")
    clock = FakeClock(datetime(2026, 9, 5, tzinfo=UTC))
    events = await CisaKevConnector(FakeHttp({"cisa.gov": fixture}), clock).fetch()  # type: ignore[arg-type]
    assert events
    kev = events[0]
    assert kev.category is Category.CYBER
    assert kev.title.startswith("CVE-")
    assert kev.url is not None and kev.url.startswith("http")
    assert kev.attributes["vendor"]
    # Entries older than the recent window are skipped.
    old_clock = FakeClock(datetime(2027, 6, 1, tzinfo=UTC))
    assert await CisaKevConnector(FakeHttp({"cisa.gov": fixture}), old_clock).fetch() == []  # type: ignore[arg-type]
    bad = {
        "vulnerabilities": [
            {"cveID": "CVE-1", "dateAdded": "not-a-date"},
            {"dateAdded": "2026-09-01"},
        ]
    }
    assert await CisaKevConnector(FakeHttp({"cisa.gov": bad}), clock).fetch() == []  # type: ignore[arg-type]


async def test_gdacs_connector() -> None:
    xml = (Path(__file__).parent / "fixtures" / "feeds" / "gdacs_rss.xml").read_text("utf-8")
    events = await GdacsConnector(FakeHttp({"gdacs.org": xml}), FakeClock(NOW)).fetch()  # type: ignore[arg-type]
    assert len(events) == 6
    types = {e.subtype for e in events}
    assert {"earthquake", "tropical_cyclone", "flood", "volcano", "wildfire"} <= types
    cyclone = next(e for e in events if e.subtype == "tropical_cyclone")
    assert cyclone.point is not None and cyclone.point.lat == 24.0 and cyclone.point.lon == 137.1
    assert cyclone.title.startswith("Green alert, tropical cyclone")
    assert cyclone.attributes["alert_level"] == "Green"
    assert cyclone.severity == 0.3
    assert cyclone.published_at.year == 2026
    assert "gdacs_green" in cyclone.tags
    assert len({e.id for e in events}) == 6
    with pytest.raises(FeedFetchError):
        await GdacsConnector(FakeHttp({"gdacs.org": "<rss><channel>"}), FakeClock(NOW)).fetch()  # type: ignore[arg-type]
    assert await GdacsConnector(FakeHttp(not_modified=True), FakeClock(NOW)).fetch() == []  # type: ignore[arg-type]


def test_registry_builds_keyless_connectors() -> None:
    connectors = build_connectors(FakeHttp(), FakeClock(NOW), disabled=["nasa_eonet", " "])  # type: ignore[arg-type]
    ids = [c.spec.id for c in connectors]
    assert "usgs_earthquakes" in ids
    assert "nasa_eonet" not in ids
    assert len(ids) == len(set(ids))
