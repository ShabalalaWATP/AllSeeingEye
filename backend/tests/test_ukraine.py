"""Ukraine war tracker: bounded control snapshot, claims kept as claims, grouped updates."""

from __future__ import annotations

import io
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import MappingProxyType

import pytest
from httpx import AsyncClient

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.isw_assessments import IswAssessmentsConnector
from ase.adapters.feeds.ukraine_general_staff import GeneralStaffLossesConnector, parse_claim
from ase.adapters.geo import ukraine_control_import as importer
from ase.adapters.geo.ukraine import load_control_snapshot, load_oblast_outlines, parse_control
from ase.adapters.geo.ukraine_oblasts_import import parse_outlines
from ase.application.ukraine import UkraineBoardService
from ase.container import Container
from ase.domain.events import Category, Point, freeze_attributes
from ase.domain.ukraine.control import MAX_SETTLEMENTS, ControlStatus
from ase.domain.ukraine.lenses import Lens, lenses_for
from ase.domain.ukraine.losses import (
    ClaimedLosses,
    claim_attributes,
    claim_from_attributes,
    war_day,
)
from ase.domain.ukraine.updates import UpdateGroup, concerns_war, update_group
from ase.domain.users import User
from feeds_helpers import NOW, FakeClock, FakeHttp, make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

FIXTURES = Path(__file__).parent / "fixtures" / "ukraine"


def cell(place_id: int, name: str, lon: float, lat: float, oblast: str = "Donets'ka") -> dict:
    ring = [[lon, lat], [lon + 0.1, lat], [lon + 0.1, lat + 0.1], [lon, lat + 0.1], [lon, lat]]
    return {
        "type": "Feature",
        "properties": {
            "geonameid": float(place_id),
            "name": name,
            "latitude": lat + 0.05,
            "longitude": lon + 0.05,
            "ADM1_NAME": oblast,
        },
        "geometry": {"type": "MultiPolygon", "coordinates": [[ring]]},
    }


CONTROL_CSV = (
    "geonameid,date,status_wiki,status_boost,status_dsm,status_isw,status,vcontrol_version\n"
    "1,20260901,RU,RU,RU,,RU,v1\n"
    "1,20260902,RU,RU,RU,,RU,v1\n"
    "2e+00,20260901,UA,UA,UA,,UA,v1\n"
    "2e+00,20260902,UA,RU,RU,,RU,v1\n"
    "3,20260901,UA,UA,UA,,UA,v1\n"
    "3,20260902,UA,UA,UA,,UA,v1\n"
    "4,20260901,UA,UA,UA,,UA,v1\n"
    "4,20260902,UA,UA,CONTESTED,,CONTESTED,v1\n"
)


def test_control_import_dissolves_cells_and_keeps_the_frontline_zone() -> None:
    places, latest = importer.read_control(io.StringIO(CONTROL_CSV))
    assert latest == "20260902" and set(places) == {1, 2, 3, 4}
    tessellation = {
        "features": [
            cell(1, "Held", 37.0, 48.0),
            cell(2, "Taken", 37.1, 48.0),
            cell(3, "Near", 37.2, 48.0, oblast="Kharkivs'ka"),
            cell(4, "Fought over", 37.0, 48.2),
            cell(5, "Unlisted", 30.0, 50.0),
        ]
    }
    snapshot = importer.build_snapshot(places, latest, tessellation, NOW)
    assert snapshot["assessment_date"] == "2026-09-02" and snapshot["release_stamp"] == "v1"
    assert snapshot["places_total"] == 4
    statuses = {row[1]: row[5] for row in snapshot["settlements"]}
    assert statuses == {"Held": "ru", "Taken": "ru", "Near": "ua", "Fought over": "contested"}
    taken = next(row for row in snapshot["settlements"] if row[1] == "Taken")
    assert taken[6] == "2026-09-02" and taken[7] == ["ua", "ru", "ru", "unknown"]
    assert [a["status"] for a in snapshot["areas"]] == ["ru", "contested"]
    assert len(snapshot["areas"][0]["polygons"]) == 1  # two adjacent cells dissolve into one
    assert snapshot["oblasts"] == [
        {"name": "Donets'ka", "total": 3, "ua": 0, "ru": 2, "contested": 1, "unknown": 0},
        {"name": "Kharkivs'ka", "total": 1, "ua": 1, "ru": 0, "contested": 0, "unknown": 0},
    ]
    assert [(c["name"], c["previous"], c["status"]) for c in snapshot["changes"]] == [
        ("Taken", "ua", "ru"),
        ("Fought over", "ua", "contested"),
    ]
    parsed = parse_control(json.loads(json.dumps(snapshot)))
    assert parsed.count(ControlStatus.RU) == 2 and len(parsed.settlements) == 4
    assert parsed.settlements[1].votes[1] is ControlStatus.RU


def test_control_import_rejects_missing_columns_and_oversized_zones() -> None:
    with pytest.raises(ValueError, match="columns"):
        importer.read_control(io.StringIO("geonameid,date\n1,20260901\n"))
    with pytest.raises(ValueError, match="no rows"):
        importer.read_control(io.StringIO(CONTROL_CSV.splitlines()[0] + "\n"))
    many = "".join(f"{i},20260901,RU,RU,RU,,RU,v1\n" for i in range(MAX_SETTLEMENTS + 1))
    places, latest = importer.read_control(io.StringIO(CONTROL_CSV.splitlines()[0] + "\n" + many))
    tessellation = {
        "features": [cell(i, f"P{i}", 30 + (i % 100) * 0.1, 45 + (i // 100) * 0.1) for i in places]
    }
    with pytest.raises(ValueError, match="bound"):
        importer.build_snapshot(places, latest, tessellation, NOW)


def test_oblast_outlines_are_simplified_and_bounded() -> None:
    ring = [[30 + i * 0.001, 50 + (i % 2) * 0.0001] for i in range(200)]
    ring += [[30.2, 50.5], [30.0, 50.5], ring[0]]
    collection = {
        "features": [
            {
                "properties": {"shapeName": "Kyiv Oblast", "shapeISO": "UA-32"},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        ]
    }
    outlines = parse_outlines(collection)
    assert outlines[0]["name"] == "Kyiv Oblast" and outlines[0]["iso"] == "UA-32"
    assert len(outlines[0]["polygons"][0][0]) < 20
    with pytest.raises(ValueError, match="count"):
        parse_outlines({"features": []})


def test_packaged_snapshots_load_within_bounds() -> None:
    snapshot = load_control_snapshot()
    outlines = load_oblast_outlines()
    assert snapshot is not None and outlines
    assert snapshot.assessment_date.year >= 2026 and snapshot.licence.startswith("ODbL")
    assert snapshot.count(ControlStatus.RU) > 1_000 and snapshot.count(ControlStatus.UA) > 20_000
    assert any(area.status is ControlStatus.RU for area in snapshot.areas)
    assert {outline.iso[:2] for outline in outlines} == {"UA"}
    assert "reported line" in snapshot.method_note


def test_claims_round_trip_through_event_attributes() -> None:
    claim = ClaimedLosses(
        reported_on=date(2026, 9, 13),
        day=1663,
        source_url="https://example.org/post",
        totals=MappingProxyType({"tanks": 12344, "personnel_units": 1506900}),
        increase=MappingProxyType({"tanks": 2}),
    )
    attributes = freeze_attributes(claim_attributes(claim))
    rebuilt = claim_from_attributes(claim.reported_on, claim.source_url, attributes)
    assert (
        rebuilt is not None
        and rebuilt.totals["tanks"] == 12344
        and rebuilt.increase == {"tanks": 2}
    )
    assert claim_from_attributes(claim.reported_on, None, {"day": 3}) is None
    assert war_day(date(2026, 9, 13)) == 1663
    assert parse_claim({"date": "bad", "day": 1, "stats": {"tanks": 1}}) is None
    assert parse_claim({"date": "2026-09-13", "day": 1, "stats": {"tanks": -1}}) is None


def test_lenses_match_vocabulary_not_meaning() -> None:
    assert lenses_for("Patriot batteries and F-16s delivered as military aid") == {Lens.EQUIPMENT}
    assert lenses_for("Mobilisation age lowered; recruits and reservists") == {Lens.WORKFORCE}
    assert lenses_for("Two civilians killed and five wounded in shelling") == {
        Lens.CASUALTIES,
        Lens.STRIKES,
    }
    assert lenses_for("Ceasefire talks and sanctions discussed at the summit") == {Lens.DIPLOMACY}
    assert lenses_for("Weather in Kyiv is mild") == frozenset()


def test_update_groups_and_war_relevance() -> None:
    assert update_group("isw_assessments") is UpdateGroup.ASSESSMENTS
    assert update_group("kyiv_independent") is UpdateGroup.UKRAINIAN
    assert update_group("meduza_en") is UpdateGroup.RUSSIAN
    assert update_group("bbc_world") is UpdateGroup.INTERNATIONAL
    filed = make_event("a", source_id="bbc_world", title="Storm hits Moscow", country_iso="RU")
    assert not concerns_war(filed)
    named = make_event("b", source_id="bbc_world", title="Kyiv reports strikes", country_iso="RU")
    assert concerns_war(named)
    assert concerns_war(make_event("c", source_id="kyiv_independent", title="Budget vote"))
    assert concerns_war(make_event("d", source_id="bbc_world", title="Vote", country_iso="UA"))


async def test_general_staff_connector_emits_one_claim_per_day() -> None:
    payload = json.loads((FIXTURES / "general_staff.json").read_text("utf-8"))
    http = FakeHttp({"russianwarship.rip": payload})
    connector = GeneralStaffLossesConnector(http, FakeClock(NOW))  # type: ignore[arg-type]
    events = await connector.fetch()
    assert "date_from=2026-06-07" in http.requests[0] and "limit=50" in http.requests[0]
    assert len(http.requests) == 1  # a short first page ends the walk
    assert len(events) == 2 and {e.subtype for e in events} == {"claimed_losses"}
    latest = max(events, key=lambda e: e.published_at or NOW)
    assert latest.attributes["total_tanks"] == 12344 and latest.attributes["day"] == 1663
    assert "claims" in latest.title and "not independently verified" in (latest.summary or "")
    assert latest.url == "https://www.facebook.com/GeneralStaff.ua/posts/example"
    assert "interested_party" in latest.tags


async def test_general_staff_connector_pages_within_the_mirror_limit() -> None:
    template = json.loads((FIXTURES / "general_staff.json").read_text("utf-8"))["data"]["records"]

    def page(first_day: int, count: int) -> dict:
        start = date(2026, 6, 7)
        rows = [
            {**template[0], "date": (start + timedelta(days=first_day + i)).isoformat()}
            for i in range(count)
        ]
        return {"data": {"records": rows}}

    http = FakeHttp({"offset=0": page(0, 50), "offset=50": page(50, 41)})
    events = await GeneralStaffLossesConnector(http, FakeClock(NOW)).fetch()  # type: ignore[arg-type]
    assert len(http.requests) == 2 and all("limit=50" in url for url in http.requests)
    assert len(events) == 91

    oversized = FakeHttp({"offset=0": page(0, 51)})
    with pytest.raises(FeedFetchError, match="more records"):
        await GeneralStaffLossesConnector(oversized, FakeClock(NOW)).fetch()  # type: ignore[arg-type]


async def test_isw_connector_keeps_only_daily_assessments_as_plain_text() -> None:
    payload = json.loads((FIXTURES / "isw_posts.json").read_text("utf-8"))
    connector = IswAssessmentsConnector(FakeHttp({"wp-json": payload}), FakeClock(NOW))  # type: ignore[arg-type]
    events = await connector.fetch()
    assert len(events) == 1
    event = events[0]
    assert event.title == "Russian Offensive Campaign Assessment, September 12, 2026"
    assert "<" not in (event.summary or "") and "Key Takeaways" in (event.summary or "")
    assert event.published_at == datetime(2026, 9, 13, 1, 38, tzinfo=UTC)
    assert event.country_iso == "UA" and event.subtype == "assessment"


def seed_events(container: Container) -> None:
    now = container.clock.now()
    inside = Point(lon=37.5, lat=48.0)
    events = [
        make_event(
            "isw",
            source_id="isw_assessments",
            category=Category.CONFLICT,
            subtype="assessment",
            title="Russian Offensive Campaign Assessment, September 12, 2026",
            summary="Key takeaways: Russian forces advanced near Pokrovsk with tanks.",
            published_at=now - timedelta(hours=3),
            observed_at=now,
            point=None,
            country_iso="UA",
        ),
        make_event(
            "ki",
            source_id="kyiv_independent",
            category=Category.NEWS,
            subtype="article",
            title="Mobilisation rules tightened",
            summary="Recruits and reservists affected.",
            published_at=now - timedelta(hours=5),
            observed_at=now,
            # Outlet articles arrive with no point and no country, as the RSS connector makes them.
            point=None,
            country_iso=None,
        ),
        make_event(
            "ru",
            source_id="meduza_en",
            category=Category.NEWS,
            subtype="article",
            title="Moscow traffic jams worsen",
            published_at=now - timedelta(hours=1),
            observed_at=now,
            point=None,
            country_iso=None,
        ),
        make_event(
            "ru-war",
            source_id="meduza_en",
            category=Category.NEWS,
            subtype="article",
            title="Drones hit Belgorod overnight",
            summary="Regional officials report damage from Ukrainian drones.",
            published_at=now - timedelta(hours=2),
            observed_at=now,
            point=None,
            country_iso=None,
        ),
        make_event(
            "located",
            source_id="reuters_world",
            category=Category.NEWS,
            subtype="article",
            title="Fighting near Pokrovsk continues",
            published_at=now - timedelta(hours=4),
            observed_at=now,
            point=inside,
            country_iso="UA",
        ),
        make_event(
            "gs",
            source_id="ukraine_general_staff",
            category=Category.CONFLICT,
            subtype="claimed_losses",
            title="General Staff of Ukraine claims cumulative Russian losses, day 1663",
            published_at=datetime(2026, 9, 13, tzinfo=UTC),
            observed_at=now,
            point=None,
            country_iso="UA",
        ).with_changes(
            attributes=freeze_attributes(
                {"day": 1663, "total_tanks": 12344, "total_personnel_units": 1506900}
            ),
            url="https://example.org/gs",
        ),
    ]
    container.store.upsert(events)


def test_board_groups_updates_and_keeps_claims_apart(container: Container) -> None:
    seed_events(container)
    service: UkraineBoardService = container.ukraine()
    board = service.board()
    groups = {entry.event.title: entry.group for entry in board.updates}
    # Outlets are read by source; a Russian item must name the war, a located item joins.
    assert groups == {
        "Russian Offensive Campaign Assessment, September 12, 2026": UpdateGroup.ASSESSMENTS,
        "Mobilisation rules tightened": UpdateGroup.UKRAINIAN,
        "Drones hit Belgorod overnight": UpdateGroup.RUSSIAN,
        "Fighting near Pokrovsk continues": UpdateGroup.INTERNATIONAL,
    }
    lenses = {entry.event.source_id: entry.lenses for entry in board.updates}
    assert lenses["kyiv_independent"] == {Lens.WORKFORCE}
    assert board.day_number == 1663 and board.day_basis == "claimed"
    assert board.claims[-1].totals["tanks"] == 12344
    assert board.freshness.claim_reported == date(2026, 9, 13)
    assert board.freshness.assessment_published is not None
    assert board.control is not None and board.control.assessment_date.year >= 2026


async def test_endpoints_require_a_session_and_serve_the_snapshot(
    client: AsyncClient, container: Container, user: User
) -> None:
    assert (await client.get("/api/conflicts/ukraine")).status_code == 401
    seed_events(container)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    board = await client.get("/api/conflicts/ukraine", headers=bearer(token))
    assert board.status_code == 200 and board.headers["cache-control"] == "private, no-store"
    body = board.json()
    assert body["day_number"] == 1663 and body["categories"]["tanks"] == "Tanks"
    assert {u["group"] for u in body["updates"]} == {
        "assessments",
        "ukrainian",
        "russian",
        "international",
    }
    assert body["control"]["counts"]["ru"] > 1_000 and body["freshness"]["control_assessed"]
    control = await client.get("/api/conflicts/ukraine/control", headers=bearer(token))
    assert control.status_code == 200
    assert control.headers["cache-control"] == "private, max-age=3600"
    payload = control.json()
    assert payload["summary"]["retained"] == len(payload["settlements"])
    assert {area["status"] for area in payload["areas"]} >= {"ru"}
    assert len(payload["outlines"]) == 27
    assert all(len(row["votes"]) == 4 for row in payload["settlements"][:50])
