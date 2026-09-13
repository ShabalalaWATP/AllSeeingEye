"""Public figures: a bounded roster, cautious name matching and placements with a stated basis."""

from __future__ import annotations

import base64
import io
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from httpx import AsyncClient
from PIL import Image
from typer.testing import CliRunner

from ase.adapters.geo import public_figures_import as importer
from ase.adapters.geo.public_figures import load_public_figures, parse_catalogue
from ase.cli import app
from ase.container import Container
from ase.domain.events import Category, GeoConfidence, Point
from ase.domain.public_figures import (
    MAX_FIGURES,
    PlacementBasis,
    PublicFigure,
    match_people,
    place_figure,
)
from ase.domain.users import User
from feeds_helpers import event_id, make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


def figure(
    key: str, name: str, aliases: tuple[str, ...] = (), person: str | None = None
) -> PublicFigure:
    return PublicFigure(
        id=key,
        wikidata_id=person or f"Q{key}",
        name=name,
        office="Office",
        role="head_of_state",
        country_iso="GB",
        organisation=None,
        aliases=aliases,
        seat_name="London",
        seat_lat=51.5,
        seat_lon=-0.12,
        portrait=None,
    )


def test_packaged_roster_is_bounded_named_and_licensed() -> None:
    catalogue = load_public_figures()
    assert 0 < len(catalogue.figures) <= MAX_FIGURES
    assert catalogue.retrieved_at.tzinfo is not None
    assert len({f.id for f in catalogue.figures}) == len(catalogue.figures)
    assert {
        "gb-head-of-government",
        "gb-defence-secretary",
        "gb-foreign-secretary",
        "ru-foreign-minister",
        "cn-defence-minister",
        "ua-head-of-state",
        "nato",
    } <= {f.id for f in catalogue.figures}
    assert all(f.role == "senior_official" for f in catalogue.figures if "-secretary" in f.id)
    with_portrait = 0
    for item in catalogue.figures:
        assert not item.name.startswith("Q"), item.id
        assert -90 <= item.seat_lat <= 90 and -180 <= item.seat_lon <= 180
        if item.portrait is None:
            continue  # the map falls back to a neutral bust
        with_portrait += 1
        png = base64.b64decode(item.portrait.png_base64)
        assert png.startswith(b"\x89PNG") and len(png) < 8_000
        assert item.portrait.licence and item.portrait.source_url.startswith("https://commons.")
    assert with_portrait >= len(catalogue.figures) - 3


def test_matching_drops_shared_titles_and_generic_surnames() -> None:
    figures = (
        figure("a", "Ada Lovelace", ("Countess of Lovelace", "His Majesty", "A. L.")),
        figure("b", "Charles III", (), "Q1"),
        figure("c", "Charles III", (), "Q1"),
        figure("d", "Carl XVI Gustaf of Sweden"),
        figure("e", "Luiz Inácio Lula da Silva"),
        figure("f", "Kim Jong-un", ("Kim Jong Un",)),
    )
    text = (
        "Lovelace spoke as His Majesty watched; Sweden and Silva were mentioned. "
        "KIM JONG UN attended, and Charles III too."
    )
    found = match_people(text, figures)
    assert found == {"Qa": "lovelace", "Qf": "kim jong un", "Q1": "charles iii"}
    assert match_people("Countess of Lovelace", figures) == {"Qa": "countess of lovelace"}
    assert match_people("A. L. and Majesty and Gustaf", figures) == {}
    assert match_people("Nothing here", figures) == {}


def test_placement_prefers_located_then_country_then_seat() -> None:
    who = figure("a", "Ada Lovelace")
    located = make_event("l", category=Category.NEWS, point=Point(lon=30.5, lat=50.4))
    country = make_event("c", category=Category.NEWS, point=Point(lon=2.0, lat=46.0)).with_changes(
        geo_confidence=GeoConfidence.COUNTRY
    )
    unlocated = make_event("u", category=Category.NEWS, point=None)
    placed = place_figure(who, (unlocated, country, located))
    assert placed.basis is PlacementBasis.REPORTED_PLACE and placed.event_id == located.id
    assert "not confirmed presence" in placed.detail
    by_country = place_figure(who, (unlocated, country))
    assert by_country.basis is PlacementBasis.REPORTED_COUNTRY and by_country.lat == 46.0
    seat = place_figure(who, (unlocated,))
    assert seat.basis is PlacementBasis.SEAT and (seat.lat, seat.lon) == (51.5, -0.12)
    assert "not an observation" in seat.detail and seat.event_id is None


def roster(**overrides: object) -> dict[str, object]:
    entry = {
        "id": "gb-head-of-state",
        "wikidata_id": "Q1",
        "name": "Ada Lovelace",
        "office": "Monarch",
        "role": "head_of_state",
        "country_iso": "GB",
        "organisation": None,
        "aliases": [],
        "seat": {"name": "London", "lat": 51.5, "lon": -0.1},
        "portrait": None,
    }
    entry.update(overrides)
    return {"retrieved_at": "2026-09-13T12:00:00+00:00", "source": "test", "figures": [entry]}


@pytest.mark.parametrize(
    "bad",
    [
        {"role": "spouse"},
        {"seat": {"name": "x", "lat": 95, "lon": 0}},
        {"country_iso": "GBR"},
        {"aliases": ["a"] * 13},
        {"portrait": {"png_base64": "<script>", "licence": "x", "credit": "y", "source_url": "z"}},
        {"name": ""},
    ],
)
def test_loader_rejects_malformed_rosters(bad: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        parse_catalogue(roster(**bad))


def test_loader_rejects_duplicates_and_oversize() -> None:
    data = roster()
    data["figures"] = [data["figures"][0]] * 2  # type: ignore[index]
    with pytest.raises(ValueError, match="unique"):
        parse_catalogue(data)
    data["figures"] = [{**roster()["figures"][0], "id": f"f{i}"} for i in range(121)]  # type: ignore[index]
    with pytest.raises(ValueError, match="bound"):
        parse_catalogue(data)
    assert parse_catalogue(roster()).figures[0].name == "Ada Lovelace"


async def test_board_places_named_figures_and_defaults_others(
    client: AsyncClient, container: Container, user: User
) -> None:
    assert (await client.get("/api/figures")).status_code == 401
    now = container.clock.now()
    container.store.upsert(
        [
            make_event(
                "n1",
                category=Category.NEWS,
                subtype="news_report",
                title="Zelenskyy visits front-line troops near Kharkiv",
                point=Point(lon=36.23, lat=49.99),
                published_at=now - timedelta(hours=2),
            ),
            make_event(
                "n2",
                category=Category.POLITICAL,
                subtype="statement",
                title="Statement from President Zelenskyy on air defence",
                point=None,
                published_at=now - timedelta(hours=1),
            ),
            make_event(
                "old",
                category=Category.NEWS,
                subtype="news_report",
                title="Zelenskyy in Paris last week",
                point=Point(lon=2.35, lat=48.85),
                published_at=now - timedelta(days=9),
            ),
        ]
    )
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/figures", headers=bearer(token))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    board = response.json()
    assert board["window_hours"] == 72 and board["events_scanned"] == 2
    assert "never means an official is at home" in board["caveat"]
    cards = {card["id"]: card for card in board["figures"]}
    ukraine = cards["ua-head-of-state"]
    assert ukraine["mentions"] == 2 and len(ukraine["latest"]) == 2
    assert ukraine["placement"]["basis"] == "reported_place"
    assert ukraine["placement"]["latitude"] == 49.99
    assert ukraine["placement"]["event_id"] == event_id("test_source", "n1")
    assert ukraine["portrait"]["png_base64"].startswith("iVBOR")
    britain = cards["gb-head-of-state"]
    assert britain["mentions"] == 0 and britain["placement"]["basis"] == "seat"
    assert britain["seat_name"] == "London"
    assert "<" not in json.dumps(board["figures"][0]["placement"])


def sparql_rows(*rows: dict[str, str]) -> httpx.Response:
    bindings = [{key: {"value": value} for key, value in row.items()} for row in rows]
    return httpx.Response(200, json={"results": {"bindings": bindings}})


def sample_jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (120, 90), (200, 40, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_office_title_prefers_declared_office_then_role_like_post() -> None:
    positions = [
        {"office": "Q9", "label": "member of parliament", "jurisdiction": "QC", "start": "2020"},
        {"office": "Q8", "label": "Prime Minister of X", "jurisdiction": "QC", "start": "2024"},
        {"office": "Q7", "label": "president of Y", "jurisdiction": "QY", "start": "2025"},
    ]
    assert importer.office_title(positions, "Q9", "QC", "head_of_state") == "Member of parliament"
    assert importer.office_title(positions, None, "QC", "head_of_government") == (
        "Prime Minister of X"
    )
    assert importer.office_title(positions, None, "QC", "head_of_state") == "President of Y"
    assert importer.office_title(positions[:1], None, "QC", "head_of_state") == "Head of state"


def test_country_entries_merge_combined_offices() -> None:
    row = {"country": "wd/Q30", "hos": "wd/Q22686", "hog": "wd/Q22686", "capLabel": "Washington"}
    entries = importer._country_entries(row, (38.9, -77.0))
    assert [e["role"] for e in entries] == ["head_of_state_and_government"]
    split = importer._country_entries({**row, "hog": "wd/Q2"}, (38.9, -77.0))
    assert [e["id"] for e in split] == ["us-head-of-state", "us-head-of-government"]


def test_circular_png_is_small_and_transparent_at_corners() -> None:
    png = importer.circular_png(sample_jpeg())
    picture = Image.open(io.BytesIO(png)).convert("RGBA")
    assert picture.size == (64, 64)
    assert picture.getpixel((0, 0))[3] == 0 and picture.getpixel((32, 32))[3] == 255
    assert len(png) < 6_000


def test_build_roster_uses_canned_sparql_and_commons(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(importer, "QUERY_PAUSE_SECONDS", 0.0)
    monkeypatch.setattr(importer, "COUNTRIES", (("US", "Q30"),))
    monkeypatch.setattr(importer, "ORGANISATIONS", importer.ORGANISATIONS[:1])
    calls: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.host)
        if request.url.host == "query.wikidata.org":
            return sparql(request.url.params.get("query", ""))
        if request.url.path == "/w/api.php":
            meta = {
                "LicenseShortName": {"value": "CC BY 4.0"},
                "Artist": {"value": "<a href='x'>Photographer &amp; Co</a>"},
            }
            page = {"imageinfo": [{"extmetadata": meta}]}
            return httpx.Response(200, json={"query": {"pages": {"1": page}}})
        return httpx.Response(200, content=sample_jpeg())

    def sparql(query: str) -> httpx.Response:
        if "wdt:P35" in query:
            return sparql_rows(
                {
                    "country": "wd/Q30",
                    "hos": "wd/Q22686",
                    "hog": "wd/Q22686",
                    "hosOffice": "wd/Q11696",
                    "capLabel": "Washington, D.C.",
                    "coord": "Point(-77.03 38.89)",
                }
            )
        if 'rdfs:label "Secretary General of NATO"' in query:
            return sparql_rows({"person": "wd/Q57792", "start": "2024"})
        if "skos:altLabel" in query:
            return sparql_rows(
                {"person": "wd/Q22686", "personLabel": "Donald Trump", "image": "x/A%20B.jpg"},
                {"person": "wd/Q57792", "personLabel": "Mark Rutte", "alias": "M. Rutte"},
            )
        if "p:P39" in query:
            return sparql_rows(
                {"person": "wd/Q22686", "pos": "wd/Q11696", "posLabel": "President of the US"}
            )
        return sparql_rows()

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        data = importer.build_roster(client, datetime(2026, 9, 13, tzinfo=UTC))
    assert data["retrieved_at"] == "2026-09-13T00:00:00+00:00"
    figures = {item["id"]: item for item in data["figures"]}
    assert set(figures) == {"us-head-of-state", "nato"}
    trump = figures["us-head-of-state"]
    assert trump["role"] == "head_of_state_and_government"
    assert trump["office"] == "President of the US" and trump["name"] == "Donald Trump"
    assert trump["portrait"]["credit"] == "Photographer & Co"
    assert trump["portrait"]["source_url"] == "https://commons.wikimedia.org/wiki/File:A%20B.jpg"
    assert figures["nato"]["portrait"] is None and figures["nato"]["aliases"] == ["M. Rutte"]
    parse_catalogue(data)
    assert "commons.wikimedia.org" in calls


def test_sparql_retries_once_after_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(importer, "QUERY_PAUSE_SECONDS", 0.0)
    monkeypatch.setattr(importer.time, "sleep", lambda _seconds: None)
    attempts = 0

    def respond(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return sparql_rows({"person": "wd/Q1"})

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert importer._sparql(client, "SELECT ?person WHERE {}") == [{"person": "wd/Q1"}]
    assert attempts == 2


def test_cli_reports_count_without_echoing_details(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "roster.json"

    def fake_import(path: str, now=None, contact: str = "") -> int:
        assert contact.startswith("https://") and "@" not in contact
        destination.write_text("{}", encoding="utf-8")
        return 3

    monkeypatch.setattr("ase.cli_public_figures.import_public_figures", fake_import)
    result = CliRunner().invoke(app, ["import-public-figures", "--destination", str(destination)])
    assert result.exit_code == 0, result.output
    assert "Wrote 3 figures" in result.output and "Review incumbents" in result.output

    def failing(path: str, now=None, contact: str = "") -> int:
        raise httpx.ConnectError("secret-host-name")

    monkeypatch.setattr("ase.cli_public_figures.import_public_figures", failing)
    result = CliRunner().invoke(app, ["import-public-figures", "--destination", str(destination)])
    assert result.exit_code == 1 and "ConnectError" in result.output
    assert "secret-host-name" not in result.output
