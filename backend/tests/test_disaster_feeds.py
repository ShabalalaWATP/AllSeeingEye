"""The disaster and humanitarian connectors added for the trackers, against captured samples."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ase.adapters.feeds.cyclones import (
    NHC_EAST_PACIFIC,
    JtwcConnector,
    NhcConnector,
    severity_from_knots,
)
from ase.adapters.feeds.emsc import EmscConnector
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.humanitarian import IfrcGoConnector, WhoOutbreakConnector
from ase.adapters.feeds.nws import NwsAlertsConnector, _centroid
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.feeds.tsunami import NTWC, TsunamiConnector
from ase.adapters.feeds.volcanoes import VolcanoReportConnector
from ase.domain.events import Category, Credibility
from ase.domain.trackers import Hazard, hazard_of
from feeds_helpers import NOW, FakeHttp
from helpers import FakeClock

FEEDS = Path(__file__).parent / "fixtures" / "feeds"


def text(name: str) -> str:
    return (FEEDS / name).read_text("utf-8")


def data(name: str) -> object:
    return json.loads(text(name))


def clock() -> FakeClock:
    return FakeClock(NOW)


async def test_nhc_reads_the_cyclone_block() -> None:
    http = FakeHttp({"index-ep.xml": text("nhc_ep.xml")})
    events = await NhcConnector(http, clock(), NHC_EAST_PACIFIC).fetch()
    assert len(events) == 1
    marie = events[0]
    assert marie.subtype == "tropical_cyclone" and hazard_of(marie) is Hazard.TROPICAL_CYCLONE
    assert marie.title.startswith("Hurricane Marie:")
    assert marie.point is not None and (marie.point.lat, marie.point.lon) == (21.4, -119.7)
    mph = float(str(marie.attributes["wind"]).split()[0])
    assert marie.severity == severity_from_knots(mph * 0.868976)
    assert marie.attributes["atcf"] == "EP132026" and "hurricane" in marie.tags
    assert marie.source_id == "nhc_east_pacific"
    assert marie.credibility is Credibility.PROBABLY_TRUE
    assert await NhcConnector(FakeHttp(not_modified=True), clock()).fetch() == []
    with pytest.raises(FeedFetchError):
        await NhcConnector(FakeHttp({"index-at.xml": "<rss><channel>"}), clock()).fetch()


class FailingHttp(FakeHttp):
    """One JTWC product cannot be fetched, as happens when a system is cancelled."""

    async def get_text(self, url: str, *, conditional: bool = True) -> str:
        if "wp2326" in url:
            raise FeedFetchError("HTTP 404")
        return await super().get_text(url, conditional=conditional)


async def test_jtwc_follows_each_warning_text() -> None:
    warning = text("jtwc_warning.txt")
    http = FakeHttp({"jtwc.rss": text("jtwc.rss"), "web.txt": warning})
    events = await JtwcConnector(http, clock()).fetch()
    assert len(events) == 5 and len(http.requests) == 6
    storm = events[0]
    assert storm.title == "Hurricane 11E (Karina), warning 035"
    assert storm.point is not None and (storm.point.lat, storm.point.lon) == (20.6, -141.6)
    assert storm.severity == 0.6 and storm.attributes["wind_knots"] == 75.0
    assert "Maximum sustained winds 75 kt" in (storm.summary or "")
    assert "Moving 285 degrees at 09 kt" in (storm.summary or "")
    assert storm.published_at.day == 5 and storm.published_at.hour == 0
    assert {"tropical_cyclone", "hurricane"} <= storm.tags
    assert severity_from_knots(None) == 0.4 and severity_from_knots(140) == 1.0
    partial = FailingHttp({"jtwc.rss": text("jtwc.rss"), "web.txt": warning})
    assert len(await JtwcConnector(partial, clock()).fetch()) == 4


async def test_volcano_report_items_carry_positions() -> None:
    http = FakeHttp({"WeeklyVolcanoRSS.xml": text("gvp_weekly.xml")})
    events = await VolcanoReportConnector(http, clock()).fetch()
    assert len(events) == 3
    ambae = events[0]
    assert ambae.subtype == "volcano" and ambae.title.startswith("Ambae, Vanuatu:")
    assert ambae.point is not None and abs(ambae.point.lat + 15.389) < 0.01
    assert ambae.severity == 0.6 and "new_eruptive_activity" in ambae.tags
    assert ambae.url is not None and ambae.url.startswith("https://volcano.si.edu/")
    assert str(ambae.attributes["period"]).startswith("20 August")


async def test_tsunami_bulletins_read_category_and_magnitude() -> None:
    http = FakeHttp({"PAAQAtom.xml": text("tsunami_paaq.xml")})
    events = await TsunamiConnector(http, clock(), NTWC).fetch()
    assert len(events) == 1
    bulletin = events[0]
    assert bulletin.title.startswith("Tsunami information:")
    assert bulletin.point is not None and bulletin.point.lat == 52.128
    assert bulletin.severity == 0.2 and "information" in bulletin.tags
    assert bulletin.attributes["magnitude"] == 5.0
    assert bulletin.url is not None and bulletin.url.startswith("https://www.tsunami.gov/")


async def test_emsc_and_nws_read_geojson_features() -> None:
    emsc = FakeHttp({"seismicportal": data("emsc.json")})
    quakes = await EmscConnector(emsc, clock()).fetch()
    assert len(quakes) == 3 and quakes[0].subtype == "earthquake"
    assert quakes[0].title.startswith("M") and quakes[0].point is not None
    assert quakes[0].url is not None and "unid=" in quakes[0].url
    assert 0.4 < (quakes[0].severity or 0) < 1.0

    nws = FakeHttp({"api.weather.gov": data("nws_alerts.json")})
    alerts = await NwsAlertsConnector(nws, clock()).fetch()
    assert len(alerts) == 2  # the alert without geometry is left out
    alert = alerts[0]
    assert alert.subtype == "severe_weather" and alert.country_iso == "US"
    assert alert.severity in (0.6, 0.8) and alert.attributes["sender"]
    assert alert.url is not None and alert.url.startswith("https://api.weather.gov/alerts/")
    assert _centroid(None) is None and _centroid({"type": "Point", "coordinates": [1, 2]}) is None


async def test_humanitarian_feeds_have_no_points_but_countries() -> None:
    who = FakeHttp({"diseaseoutbreaknews": data("who_don.json")})
    outbreaks = await WhoOutbreakConnector(who, clock()).fetch()
    assert len(outbreaks) == 3 and outbreaks[0].category is Category.HUMANITARIAN
    assert outbreaks[0].point is None and outbreaks[0].subtype == "outbreak"
    assert outbreaks[0].url is not None
    assert outbreaks[0].url.endswith(str(outbreaks[0].attributes["slug"]))

    ifrc = FakeHttp({"goadmin.ifrc.org": data("ifrc_go.json")})
    emergencies = await IfrcGoConnector(ifrc, clock()).fetch()
    assert len(emergencies) == 2
    flood = emergencies[0]
    assert flood.subtype == "emergency" and flood.country_iso == "PH"
    assert flood.severity == 0.3 and "flood" in flood.tags and "yellow" in flood.tags
    assert flood.url == "https://go.ifrc.org/emergencies/8076"


def test_registry_includes_the_new_connectors() -> None:
    ids = {connector.spec.id for connector in build_connectors(FakeHttp(), clock())}
    assert {
        "emsc_earthquakes",
        "nhc_atlantic",
        "nhc_east_pacific",
        "jtwc",
        "gvp_weekly",
        "ntwc_tsunami",
        "ptwc_tsunami",
        "nws_alerts",
        "who_don",
        "ifrc_go",
    } <= ids
