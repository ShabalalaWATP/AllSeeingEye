"""The adsb.lol connector keeps one moving event per aircraft and drops unusable rows."""

from __future__ import annotations

from datetime import timedelta

from ase.adapters.feeds.adsb import AdsbMilitaryConnector
from ase.domain.events import Category, Credibility, GeoConfidence, event_id
from feeds_helpers import NOW, FakeClock, FakeHttp, load_fixture


async def test_aircraft_become_events() -> None:
    http = FakeHttp({"api.adsb.lol": load_fixture("adsb_mil.json")})
    events = await AdsbMilitaryConnector(http, FakeClock(NOW)).fetch()  # type: ignore[arg-type]
    assert [event.attributes["icao_hex"] for event in events] == ["ae4e0e", "ae1234"]
    herc, bomber = events
    assert herc.id == event_id("adsb", "ae4e0e")
    assert herc.category is Category.AVIATION and herc.subtype == "military_aircraft"
    assert herc.title == "RH451 (C30J)"
    assert herc.summary is not None
    assert herc.summary.startswith("Airborne at 22250 ft, 250 kt, track 109°, squawk 3404.")
    assert herc.url == "https://globe.adsb.lol/?icao=ae4e0e"
    assert herc.point is not None and herc.point.lat == 61.265724
    assert herc.geo_confidence is GeoConfidence.EXACT
    assert herc.published_at == NOW - timedelta(seconds=0.334)
    assert herc.credibility is Credibility.PROBABLY_TRUE
    assert {"military", "adsb", "c30j"} <= herc.tags
    assert herc.attributes["callsign"] == "RH451"
    assert herc.attributes["squawk"] == "3404"
    assert herc.attributes["mlat"] is False and herc.attributes["on_ground"] is False
    assert bomber.title == "60-0001 (B52)"
    assert bomber.attributes["on_ground"] is True and bomber.attributes["altitude_ft"] is None
    assert bomber.attributes["mlat"] is True and bomber.attributes["callsign"] is None
    assert bomber.summary is not None and bomber.summary.startswith("On the ground, 0 kt")


async def test_movement_changes_the_hash_and_faults_are_tolerated() -> None:
    fixture = load_fixture("adsb_mil.json")
    before = await AdsbMilitaryConnector(FakeHttp({"adsb": fixture}), FakeClock(NOW)).fetch()  # type: ignore[arg-type]
    fixture["ac"][0]["lat"] += 0.01
    after = await AdsbMilitaryConnector(FakeHttp({"adsb": fixture}), FakeClock(NOW)).fetch()  # type: ignore[arg-type]
    assert before[0].id == after[0].id
    assert before[0].content_hash != after[0].content_hash
    assert await AdsbMilitaryConnector(FakeHttp(not_modified=True), FakeClock(NOW)).fetch() == []  # type: ignore[arg-type]
    assert (
        await AdsbMilitaryConnector(
            FakeHttp({"adsb": ["not", "a", "dict"]}), FakeClock(NOW)
        ).fetch()
        == []
    )  # type: ignore[arg-type]
    assert (
        await AdsbMilitaryConnector(FakeHttp({"adsb": {"ac": ["junk", 3]}}), FakeClock(NOW)).fetch()
        == []
    )  # type: ignore[arg-type]
