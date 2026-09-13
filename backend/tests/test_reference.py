"""Reference notes: bounded packaged catalogue, cautious key matching, authenticated lookups."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from httpx import AsyncClient
from typer.testing import CliRunner

from ase.adapters import reference_import as importer
from ase.adapters.reference import load_reference, parse_catalogue
from ase.cli import app
from ase.domain.reference import ReferenceCatalogue, normalise_key
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token


def test_packaged_catalogue_is_bounded_and_linked() -> None:
    catalogue = load_reference()
    assert catalogue.retrieved_at.tzinfo is not None
    assert 1000 <= len(catalogue.entries["vessel"]) <= 4000
    assert 100 <= len(catalogue.entries["aircraft"]) <= 1000
    assert 20 <= len(catalogue.entries["aircraft_type"]) <= 300
    for table in catalogue.entries.values():
        for entry in list(table.values())[:100]:
            assert entry.name and entry.links
            assert all(link.url.startswith("https://") for link in entry.links)
    sentry = catalogue.lookup("aircraft_type", ("e3tf",))
    assert sentry and "Sentry" in sentry[0].name


@pytest.mark.parametrize(
    ("kind", "raw", "expected"),
    [
        ("vessel", " 165327752 ", "165327752"),
        ("vessel", "MMSI 165327752", "165327752"),
        ("vessel", "12345", ""),
        ("aircraft", "n-x-211", "NX211"),
        ("aircraft", "G ABCD", "GABCD"),
        ("aircraft_type", "e3tf", "E3TF"),
        ("aircraft_type", "x", ""),
        ("aircraft", "a" * 40, ""),
    ],
)
def test_keys_are_normalised_before_matching(kind, raw: str, expected: str) -> None:
    assert normalise_key(kind, raw) == expected


def small_catalogue() -> ReferenceCatalogue:
    return parse_catalogue(
        {
            "retrieved_at": "2026-09-13T12:00:00+00:00",
            "source": "test",
            "vessel": [
                {
                    "key": "165327752",
                    "name": "HMS Argyll",
                    "description": "Type 23 frigate",
                    "detail": "frigate",
                    "links": [
                        {"label": "Wikipedia", "url": "https://en.wikipedia.org/wiki/HMS_Argyll"},
                        {"label": "Bad", "url": "javascript:alert(1)"},
                    ],
                },
                {"key": "bad", "name": "Dropped"},
                {"key": "165327752", "name": "Duplicate"},
            ],
            "aircraft": [{"key": "N-X-211", "name": "Spirit of St. Louis", "links": []}],
            "aircraft_type": [],
        }
    )


def test_parser_drops_bad_keys_unsafe_links_and_duplicates() -> None:
    catalogue = small_catalogue()
    (argyll,) = catalogue.lookup("vessel", ("165327752", "165327752", "nope"))
    assert argyll.name == "HMS Argyll" and [link.label for link in argyll.links] == ["Wikipedia"]
    assert argyll.provenance == "test"
    assert catalogue.lookup("aircraft", ("nx211",))[0].name == "Spirit of St. Louis"
    assert catalogue.lookup("aircraft_type", ("E3TF",)) == ()
    with pytest.raises(ValueError, match="bound"):
        parse_catalogue(
            {
                "retrieved_at": "2026-09-13T12:00:00+00:00",
                "vessel": [{"key": str(100000000 + i), "name": "x"} for i in range(4001)],
            }
        )


async def test_lookup_requires_login_and_returns_matches_only(
    client: AsyncClient, user: User
) -> None:
    assert (await client.get("/api/reference?kind=vessel&keys=165327752")).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get(
        "/api/reference?kind=aircraft_type&keys=e3tf,unknown,r135", headers=bearer(token)
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    payload = response.json()
    assert [item["key"] for item in payload["items"]] == ["E3TF", "R135"]
    assert payload["items"][0]["links"][0]["url"].startswith("https://en.wikipedia.org/")
    assert "not confirmation of identity" in payload["caveat"]
    bad = await client.get("/api/reference?kind=spouse&keys=x", headers=bearer(token))
    assert bad.status_code == 422
    many = await client.get(
        "/api/reference?kind=aircraft_type&keys=" + ",".join(["x"] * 60 + ["e3tf"]),
        headers=bearer(token),
    )
    assert many.status_code == 200 and many.json()["items"] == []  # only the first 50 keys count
    huge = await client.get("/api/reference?kind=vessel&keys=" + "1" * 2000, headers=bearer(token))
    assert huge.status_code == 422


def test_import_parsers_keep_one_note_per_identifier() -> None:
    vessels = importer.parse_vessels(
        [
            {
                "item": "http://www.wikidata.org/entity/Q1",
                "itemLabel": "HMS Argyll",
                "mmsi": "165327752",
                "imo": "8949599",
                "iso": "GB",
                "typeLabel": "frigate",
                "desc": "Type 23 frigate",
                "site": "https://en.wikipedia.org/wiki/HMS_Argyll_(F231)",
            },
            {
                "item": "http://www.wikidata.org/entity/Q1",
                "itemLabel": "HMS Argyll",
                "mmsi": "165327752",
                "typeLabel": "ship",
            },
            {"item": "http://www.wikidata.org/entity/Q2", "itemLabel": "Q2", "mmsi": "111111111"},
            {"item": "http://www.wikidata.org/entity/Q3", "itemLabel": "Short", "mmsi": "123"},
        ]
    )
    assert len(vessels) == 1
    assert vessels[0]["detail"] == "frigate · flag GB · IMO 8949599"
    assert [link["label"] for link in vessels[0]["links"]] == ["Wikipedia", "Wikidata"]
    aircraft = importer.parse_aircraft(
        [
            {
                "item": "http://www.wikidata.org/entity/Q9",
                "itemLabel": "Clipper Victor",
                "reg": "N736PA",
                "operatorLabel": "Pan Am",
            },
            {
                "item": "http://www.wikidata.org/entity/Q9",
                "itemLabel": "Clipper Victor",
                "reg": "N736PA",
            },
            {"item": "http://www.wikidata.org/entity/Q8", "itemLabel": "Bad", "reg": "x"},
        ]
    )
    assert [a["key"] for a in aircraft] == ["N736PA"] and aircraft[0]["detail"] == "Pan Am"
    assert len(importer.curated_aircraft_types()) >= 20


def test_import_writes_snapshot_from_canned_sparql(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(importer.time, "sleep", lambda _s: None)

    def respond(request: httpx.Request) -> httpx.Response:
        query = request.url.params.get("query", "")
        if "P587" in query:
            rows = [
                {
                    "item": {"value": "wd/Q1"},
                    "itemLabel": {"value": "Ship"},
                    "mmsi": {"value": "123456789"},
                }
            ]
        else:
            rows = [
                {
                    "item": {"value": "wd/Q2"},
                    "itemLabel": {"value": "Plane"},
                    "reg": {"value": "G-ABCD"},
                }
            ]
        return httpx.Response(200, json={"results": {"bindings": rows}})

    real = httpx.Client
    monkeypatch.setattr(
        importer.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(respond), **kw)
    )
    destination = tmp_path / "reference.json"
    counts = importer.import_reference(str(destination))
    assert counts["vessel"] == 1 and counts["aircraft"] == 1 and counts["aircraft_type"] >= 20
    data = json.loads(destination.read_text("utf-8"))
    assert datetime.fromisoformat(data["retrieved_at"]) <= datetime.now(UTC)
    assert parse_catalogue(data).lookup("aircraft", ("gabcd",))[0].name == "Plane"


def test_cli_reports_counts_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ase.cli_reference.import_reference",
        lambda *a, **k: {"vessel": 2, "aircraft": 1, "aircraft_type": 39},
    )
    result = CliRunner().invoke(
        app, ["import-reference", "--destination", str(tmp_path / "r.json")]
    )
    assert (
        result.exit_code == 0
        and "Wrote 2 vessels, 1 aircraft and 39 aircraft types" in result.output
    )

    def failing(*a: object, **k: object) -> dict[str, int]:
        raise httpx.ConnectError("hidden-host")

    monkeypatch.setattr("ase.cli_reference.import_reference", failing)
    result = CliRunner().invoke(
        app, ["import-reference", "--destination", str(tmp_path / "r.json")]
    )
    assert result.exit_code == 1 and "ConnectError" in result.output
    assert "hidden-host" not in result.output
