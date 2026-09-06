"""NAVAREA warnings, satellites, launches, the K index, ransomware claims and outage alerts."""

from __future__ import annotations

import copy
from datetime import UTC, datetime

from ase.adapters.feeds.cyber import IodaConnector, RansomwareConnector, _country_of
from ase.adapters.feeds.navarea import NavareaConnector, issued, kind_of, positions
from ase.adapters.feeds.registry import build_connectors
from ase.adapters.feeds.space import (
    KpConnector,
    LaunchConnector,
    SatelliteConnector,
    kp_severity,
    subpoint,
)
from ase.adapters.geo.countries import CountryIndex
from ase.application.feeds.geo import CountryStage
from ase.domain.events import Category, Credibility, GeoConfidence, Point
from feeds_helpers import NOW, FakeHttp, load_fixture, make_event
from helpers import FakeClock


def clock() -> FakeClock:
    return FakeClock(NOW)


def test_navarea_helpers_read_positions_dates_and_kinds() -> None:
    found = positions("PORT OF BALTIMORE 39-16.00N 076-35.00W AND 12-10.50S 068-52.00E")
    assert len(found) == 2
    assert (round(found[0].lat, 4), round(found[0].lon, 4)) == (39.2667, -76.5833)
    assert (round(found[1].lat, 3), round(found[1].lon, 3)) == (-12.175, 68.867)
    assert issued("081653Z MAY 2024", NOW) == datetime(2024, 5, 8, 16, 53, tzinfo=UTC)
    assert issued("garbage", NOW) == NOW and issued("311200Z FEB 2024", NOW) == NOW
    assert kind_of("GUNNERY EXERCISE IN AREA") == ("military_exercise", 0.6)
    assert kind_of("SUSPICIOUS APPROACH BY SKIFF") == ("security", 0.8)
    assert kind_of("GPS INTERFERENCE REPORTED") == ("gnss", 0.7)
    assert kind_of("LIGHT UNLIT") == ("hazard", 0.3)
    assert kind_of("DSC SERVICES OFF AIR") == ("navigation", 0.3)


async def test_navarea_connector_places_warnings_with_positions() -> None:
    http = FakeHttp({"broadcast-warn": load_fixture("navarea.json")})
    events = await NavareaConnector(http, clock()).fetch()
    assert len(events) == 4 and len({event.id for event in events}) == 3  # the sample repeats one
    first = events[0]
    assert first.category is Category.MARITIME and first.subtype == "navarea_warning"
    assert first.title.startswith("NAVAREA 4 2024/517:")
    assert first.published_at == datetime(2024, 5, 8, 16, 53, tzinfo=UTC)
    assert "navarea_4" in first.tags and first.attributes["message"] == "2024/517"
    assert first.credibility is Credibility.PROBABLY_TRUE
    located = [event for event in events if event.point is not None]
    assert located and all(event.geo_confidence is GeoConfidence.EXACT for event in located)
    assert all(event.attributes["positions"] >= 1 for event in located)


async def test_satellites_are_propagated_and_elements_cached() -> None:
    http = FakeHttp({"gp.php": load_fixture("celestrak_stations.json")})
    connector = SatelliteConnector(http, clock())
    events = await connector.fetch()
    assert [event.title for event in events] == ["ISS (ZARYA)", "POISK"]
    iss = events[0]
    assert iss.category is Category.SPACE and iss.subtype == "satellite"
    assert iss.point is not None and -180 <= iss.point.lon <= 180 and -52 <= iss.point.lat <= 52
    altitude = iss.attributes["altitude_km"]
    assert isinstance(altitude, float) and 350 <= altitude <= 480
    assert 7 <= iss.attributes["speed_km_s"] <= 8
    again = await connector.fetch()
    assert len(again) == 2 and len(http.requests) == 1  # elements reused within two hours
    point, height = subpoint((7000.0, 0.0, 0.0), NOW)
    assert round(height) == 629 and point.lat == 0.0
    assert (
        await SatelliteConnector(FakeHttp({"gp.php": [{"OBJECT_NAME": "junk"}]}), clock()).fetch()
        == []
    )


async def test_launches_and_the_k_index() -> None:
    launches = await LaunchConnector(
        FakeHttp({"launches/upcoming": load_fixture("launches.json")}), clock()
    ).fetch()
    assert len(launches) == 2
    spectrum = launches[0]
    assert spectrum.subtype == "launch" and spectrum.title.startswith("Launch: Spectrum")
    assert spectrum.point is not None and round(spectrum.point.lat, 1) == 69.1
    assert str(spectrum.attributes["net"]).startswith("2026-09-05T20:00")
    assert spectrum.attributes["provider"] == "Isar Aerospace"

    kp = await KpConnector(
        FakeHttp({"planetary-k-index": load_fixture("swpc_kp.json")}), clock()
    ).fetch()
    assert len(kp) == 1 and kp[0].title == "Planetary K index 2.00: quiet"
    assert kp[0].severity == 0.2 and kp[0].attributes["kp"] == 2.0 and kp[0].point is None
    assert kp_severity(7.5) == 0.9 and kp_severity(5) == 0.6 and kp_severity(4.2) == 0.4
    assert await KpConnector(FakeHttp({"planetary-k-index": []}), clock()).fetch() == []


async def test_ransomware_claims_and_outage_alerts() -> None:
    claims = await RansomwareConnector(
        FakeHttp({"recentvictims": load_fixture("ransomware.json")}), clock()
    ).fetch()
    assert len(claims) == 3
    paylogix = claims[0]
    assert paylogix.title == "Paylogix: claimed by akira (Financial Services)"
    assert paylogix.country_iso == "US" and paylogix.geo_confidence is GeoConfidence.COUNTRY
    assert paylogix.credibility is Credibility.POSSIBLY_TRUE and paylogix.point is None
    assert paylogix.url is not None and paylogix.url.startswith("https://www.ransomware.live/id/")
    assert "akira" in paylogix.tags and paylogix.attributes["sector"] == "Financial Services"

    alerts = copy.deepcopy(load_fixture("ioda_alerts.json"))
    alerts["data"][0]["level"] = "warning"  # the Tunisia alert becomes reportable
    outages = await IodaConnector(FakeHttp({"outages/alerts": alerts}), clock()).fetch()
    assert len(outages) == 2  # normal-level alerts are recoveries and are left out
    tunisia = next(event for event in outages if event.country_iso == "TN")
    assert tunisia.subtype == "outage" and tunisia.severity == 0.5
    assert tunisia.geo_confidence is GeoConfidence.COUNTRY
    assert tunisia.url == "https://ioda.inetintel.cc.gatech.edu/country/TN"
    critical = next(event for event in outages if event.severity == 0.8)
    assert critical.country_iso is None and str(critical.attributes["datasource"]) in critical.tags
    assert _country_of({"type": "geoasn", "code": "37405-NG"}) == "NG"
    assert _country_of({"type": "region", "code": "2947"}) is None


def test_country_stage_preserves_country_only_evidence_without_inventing_coordinates() -> None:
    countries = CountryIndex.from_resource()
    stage = CountryStage(countries, countries)
    country_level = make_event("a", point=None, country_iso="TN").with_changes(
        geo_confidence=GeoConfidence.COUNTRY
    )
    unknown_confidence = make_event("b", point=None, country_iso="TN")
    located = make_event("c", point=Point(10.0, 36.8), country_iso=None)
    placed, untouched, resolved = stage.process([country_level, unknown_confidence, located])
    assert placed.point is None
    assert placed.country_iso == "TN"
    assert placed.geo_confidence is GeoConfidence.COUNTRY
    assert placed is country_level
    assert untouched.point is None
    assert resolved.country_iso == "TN"
    assert CountryStage(countries).process([country_level])[0].point is None


def test_registry_includes_the_new_connectors() -> None:
    ids = {connector.spec.id for connector in build_connectors(FakeHttp(), clock())}
    assert {
        "nga_navarea",
        "celestrak_stations",
        "launch_library",
        "swpc_kp",
        "ransomware_live",
        "ioda_outages",
    } <= ids
