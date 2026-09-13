"""Infrastructure imports parse bounded public records and keep curated entries first."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from ase.adapters.geo import infrastructure_import as importer
from ase.adapters.geo import sites_osm
from ase.adapters.geo.countries import CountryIndex, load_records
from ase.adapters.geo.infrastructure import public_infrastructure
from ase.api.schemas_infrastructure import InfrastructureOut
from ase.cli import app


def test_packaged_snapshot_carries_data_centres_and_imported_stations() -> None:
    data = InfrastructureOut.model_validate(public_infrastructure())
    assert 1000 <= len(data.data_centres) <= 3700
    assert len({c.id for c in data.data_centres}) == len(data.data_centres)
    assert "OpenStreetMap" in data.data_centre_attribution
    assert data.data_centre_licence_url == "https://www.openstreetmap.org/copyright"
    for centre in [c for c in data.data_centres if c.id.startswith("osm-")][:200]:
        assert centre.source_url.startswith("https://www.openstreetmap.org/")
        assert centre.website is None or centre.website.startswith("https://")
        assert centre.country is None or len(centre.country) == 2
    imported = [s for s in data.ground_stations if s.id.startswith("wd-")]
    assert len(imported) >= 50
    assert all(s.source_url.startswith("https://") for s in imported)
    assert any(s.wikipedia for s in imported)


def test_station_rows_are_deduplicated_and_merged_behind_curated() -> None:
    rows = [
        {
            "item": "http://www.wikidata.org/entity/Q1",
            "itemLabel": "Alpha Station",
            "coord": "Point(10.5 50.5)",
            "operatorLabel": "Agency A",
            "iso": "DE",
            "site": "https://en.wikipedia.org/wiki/Alpha",
            "web": "http://alpha.example",
        },
        {
            "item": "http://www.wikidata.org/entity/Q1",
            "itemLabel": "Alpha Station",
            "coord": "Point(10.5 50.5)",
            "operatorLabel": "Agency B",
            "iso": "DE",
        },
        {
            "item": "http://www.wikidata.org/entity/Q2",
            "itemLabel": "Q2",
            "coord": "Point(1 1)",
            "iso": "FR",
        },
        {
            "item": "http://www.wikidata.org/entity/Q3",
            "itemLabel": "No country",
            "coord": "Point(1 1)",
        },
        {
            "item": "http://www.wikidata.org/entity/Q4",
            "itemLabel": "Near curated",
            "coord": "Point(21.08 67.89)",
            "iso": "SE",
        },
    ]
    parsed = importer.parse_station_rows(rows)
    assert [s["id"] for s in parsed] == ["wd-q1", "wd-q4"]
    alpha = parsed[0]
    assert alpha["operator"] == "Agency A" and alpha["website"] is None
    assert alpha["wikipedia"] == "https://en.wikipedia.org/wiki/Alpha"
    curated = [
        {"id": "esrange", "name": "Esrange", "longitude": 21.07, "latitude": 67.88, "country": "SE"}
    ]
    merged = importer.merge_stations(curated, parsed)
    assert [s["id"] for s in merged] == ["esrange", "wd-q1"]


def test_centre_elements_resolve_country_and_skip_malformed() -> None:
    index = CountryIndex(load_records())
    elements = [
        {
            "type": "node",
            "id": 1,
            "lat": 51.5,
            "lon": -0.1,
            "tags": {"name": "London DC", "operator": "Op", "website": "https://op.example"},
        },
        {
            "type": "way",
            "id": 2,
            "center": {"lat": 48.85, "lon": 2.35},
            "tags": {"name": "Paris DC", "brand": "Brand"},
        },
        {"type": "way", "id": 3, "center": {"lat": 48.85, "lon": 2.35}, "tags": {}},
        {"type": "node", "id": 4, "lat": 95, "lon": 0, "tags": {"name": "Bad"}},
        {"type": "node", "id": "x", "lat": 1, "lon": 1, "tags": {"name": "Bad id"}},
    ]
    centres = importer.parse_centre_elements(elements, index)
    assert [c["id"] for c in centres] == ["osm-way-2", "osm-node-1"]
    assert centres[1]["country"] == "GB" and centres[1]["website"] == "https://op.example"
    assert centres[0]["country"] == "FR" and centres[0]["operator"] == "Brand"
    assert centres[0]["website"] is None


def test_import_data_centres_writes_attributed_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "overpass-api.de"
        return httpx.Response(
            200,
            json={
                "osm3s": {"timestamp_osm_base": "2026-09-13T00:00:00Z"},
                "elements": [
                    {
                        "type": "node",
                        "id": 1,
                        "lat": 51.5,
                        "lon": -0.1,
                        "tags": {"name": "London DC"},
                    }
                ],
            },
        )

    real = httpx.Client
    monkeypatch.setattr(
        importer.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(respond), **kw)
    )
    monkeypatch.setattr(sites_osm.time, "sleep", lambda _s: None)

    class Offline:
        def search(self, text: str, limit: int = 5) -> list[tuple[str, str, str]]:
            return []

        def facts(self, qids: list[str]) -> dict[str, object]:
            return {}

        def close(self) -> None:
            return None

    monkeypatch.setattr(importer.WikidataEntities, "open", classmethod(lambda cls, c: Offline()))
    destination = tmp_path / "data_centres.json"
    assert importer.import_data_centres(str(destination)) == 1
    snapshot = json.loads(destination.read_text("utf-8"))
    assert snapshot["items"][0]["id"] == "osm-node-1" and snapshot["licence_url"].endswith(
        "copyright"
    )
    assert snapshot["items"][0]["links"] == [
        {"label": "OpenStreetMap feature", "url": "https://www.openstreetmap.org/node/1"}
    ]
    assert snapshot["items"][0]["precision"] == "mapped"


def test_cli_commands_report_counts_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ase.cli_infrastructure.import_ground_stations", lambda *a, **k: 30)
    result = CliRunner().invoke(
        app, ["import-ground-stations", "--destination", str(tmp_path / "g.json")]
    )
    assert result.exit_code == 0 and "Wrote 30 ground stations" in result.output

    def failing(*a: object, **k: object) -> int:
        raise httpx.ConnectError("overpass-host")

    monkeypatch.setattr("ase.cli_infrastructure.import_data_centres", failing)
    result = CliRunner().invoke(
        app, ["import-data-centres", "--destination", str(tmp_path / "d.json")]
    )
    assert result.exit_code == 1 and "ConnectError" in result.output
    assert "overpass-host" not in result.output
