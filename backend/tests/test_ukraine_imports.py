"""Ukraine importers end to end on a mock transport, loader validation and the CLI commands."""

from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from shapely.geometry import LineString, MultiPolygon, Polygon
from typer.testing import CliRunner

from ase.adapters.geo import bounded_download, ukraine_control_import, ukraine_oblasts_import
from ase.adapters.geo.ukraine import parse_control, parse_outlines
from ase.adapters.geo.ukraine_geometry import polygon_lists
from ase.cli import app
from ase.domain.ukraine.control import (
    ControlArea,
    ControlSnapshot,
    ControlStatus,
    OblastControl,
    SettlementControl,
)

CSV = (
    "geonameid,date,status_wiki,status_boost,status_dsm,status_isw,status,vcontrol_version\n"
    "1,20260901,RU,RU,RU,,RU,v1\n"
    "1,20260902,RU,RU,RU,,RU,v1\n"
    "2,20260901,UA,UA,UA,,UA,v1\n"
    "2,20260902,UA,UA,UA,,UA,v1\n"
)


def square(place_id: int, name: str, lon: float, lat: float) -> dict[str, Any]:
    ring = [[lon, lat], [lon + 0.1, lat], [lon + 0.1, lat + 0.1], [lon, lat + 0.1], [lon, lat]]
    return {
        "type": "Feature",
        "properties": {
            "geonameid": place_id,
            "name": name,
            "latitude": lat + 0.05,
            "longitude": lon + 0.05,
            "ADM1_NAME": "Kherson",
        },
        "geometry": {"type": "MultiPolygon", "coordinates": [[ring]]},
    }


def control_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("control_latest_2026.csv", CSV)
    return buffer.getvalue()


def mock_client(monkeypatch: pytest.MonkeyPatch, module: Any, routes: dict[str, Any]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        for key, payload in routes.items():
            if key in str(request.url):
                if isinstance(payload, bytes):
                    return httpx.Response(200, content=payload)
                return httpx.Response(200, json=payload)
        return httpx.Response(404)

    real = httpx.Client

    def client(**kwargs: Any) -> httpx.Client:
        kwargs.pop("timeout", None)
        return real(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(module.httpx, "Client", client)


def test_control_import_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    tessellation = {"features": [square(1, "Held", 33.0, 46.5), square(2, "Free", 33.1, 46.5)]}
    mock_client(
        monkeypatch,
        ukraine_control_import,
        {"control_latest_2026.zip": control_zip(), "gn_UA_tess.geojson": tessellation},
    )
    destination = tmp_path / "control.json"
    assert ukraine_control_import.import_ukraine_control(str(destination), year=2026) == 2
    snapshot = parse_control(json.loads(destination.read_text("utf-8")))
    assert snapshot.assessment_date == date(2026, 9, 2)
    assert snapshot.count(ControlStatus.RU) == 1 and snapshot.areas[0].vertices >= 5
    assert snapshot.licence == "ODbL 1.0" and "Zhukov" in snapshot.attribution


def test_control_archive_must_hold_one_bounded_csv(tmp_path: Path) -> None:
    path = tmp_path / "two.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("a.csv", CSV)
        archive.writestr("b.csv", CSV)
    with pytest.raises(ValueError, match="exactly one"):
        ukraine_control_import._control_from_zip(path)


def test_control_reader_counts_actual_inflated_bytes() -> None:
    source = io.BytesIO(b"12345")
    reader = ukraine_control_import._BoundedReader(source, 4)
    with pytest.raises(ValueError, match="inflated byte limit"):
        reader.read()


def test_control_reader_retains_only_two_runs_per_place() -> None:
    rows = [
        "geonameid,date,status_wiki,status_boost,status_dsm,status_isw,status",
        *(f"1,202609{day:02d},UA,UA,UA,UA,{('UA' if day % 2 else 'RU')}" for day in range(1, 10)),
    ]
    places, latest = ukraine_control_import.read_control(io.StringIO("\n".join(rows)))
    assert latest == "20260909"
    assert len(places[1].runs) == 2
    assert [status.value for _, status in places[1].runs] == ["ru", "ua"]


def test_oblast_import_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ring = [[30, 50], [31, 50], [31, 51], [30, 51], [30, 50]]
    collection = {
        "features": [
            {
                "properties": {"shapeName": "Kyiv Oblast", "shapeISO": "UA-32"},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        ]
    }
    mock_client(
        monkeypatch,
        ukraine_oblasts_import,
        {
            "geoboundaries.org/api": {
                "simplifiedGeometryGeoJSON": "https://example.test/outlines.geojson"
            },
            "outlines.geojson": collection,
        },
    )
    destination = tmp_path / "oblasts.json"
    assert ukraine_oblasts_import.import_ukraine_oblasts(str(destination)) == 1
    outlines = parse_outlines(json.loads(destination.read_text("utf-8")))
    assert outlines[0].name == "Kyiv Oblast" and outlines[0].vertices == 5


def test_oblast_import_requires_a_download_link(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_client(monkeypatch, ukraine_oblasts_import, {"geoboundaries.org/api": {}})
    with pytest.raises(ValueError, match="download link"):
        ukraine_oblasts_import.import_ukraine_oblasts("unused.json")


def test_bounded_download_enforces_https_and_the_ceiling(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "declared" in str(request.url):
            return httpx.Response(200, content=b"x" * 10, headers={"content-length": "10"})
        return httpx.Response(200, content=iter([b"y" * 5, b"y" * 5]))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    target = tmp_path / "file.bin"
    with pytest.raises(ValueError, match="https"):
        bounded_download.download_to(client, "http://example.test/a", target, 100)
    with pytest.raises(ValueError, match="declares"):
        bounded_download.download_to(client, "https://example.test/declared", target, 5)
    with pytest.raises(ValueError, match="exceeded"):
        bounded_download.download_to(client, "https://example.test/stream", target, 5)
    assert bounded_download.download_to(client, "https://example.test/stream", target, 10) == 10
    assert "github.com" in bounded_download.user_agent(bounded_download.DEFAULT_CONTACT)


def test_polygon_lists_handles_every_geometry_type() -> None:
    box = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    assert len(polygon_lists(box)) == 1 and len(polygon_lists(MultiPolygon([box, box]))) == 2
    assert polygon_lists(LineString([(0, 0), (1, 1)])) == []
    assert polygon_lists(box.intersection(LineString([(0, 0), (1, 1)]))) == []


def test_loader_rejects_malformed_rows_and_geometry() -> None:
    good = {
        "assessment_date": "2026-09-02",
        "release_stamp": "v1",
        "retrieved_at": "2026-09-13T00:00:00+00:00",
        "attribution": "A",
        "licence": "ODbL 1.0",
        "source_url": "https://example.test",
        "method_note": "M",
        "places_total": 1,
        "settlements": [
            [1, "Place", "Oblast", 48.0, 37.0, "ru", None, ["ru", "ru", "ru", "unknown"]]
        ],
        "areas": [],
        "oblasts": [{"name": "Oblast", "total": 1, "ua": 0, "ru": 1, "contested": 0, "unknown": 0}],
        "changes": [],
    }
    assert parse_control(good).count(ControlStatus.RU) == 1
    bad_rows: list[Any] = [
        [1, "Place", "Oblast", 48.0, 37.0, "ru", None],
        [1, "Place", "Oblast", 99.0, 37.0, "ru", None, ["ru", "ru", "ru", "unknown"]],
        [1, "Place", "Oblast", 48.0, 37.0, "ru", None, ["ru"]],
        [1, "Place", "Oblast", 48.0, 37.0, "elsewhere", None, ["ru", "ru", "ru", "unknown"]],
        [1, 5, "Oblast", 48.0, 37.0, "ru", None, ["ru", "ru", "ru", "unknown"]],
    ]
    for row in bad_rows:
        with pytest.raises(ValueError):
            parse_control({**good, "settlements": [row]})
    with pytest.raises(ValueError, match="range"):
        parse_control({**good, "areas": [{"status": "ru", "polygons": [[[[200.0, 0.0]]]]}]})
    with pytest.raises(ValueError, match="list"):
        parse_control({**good, "areas": [{"status": "ru", "polygons": "no"}]})
    with pytest.raises(ValueError, match="text"):
        parse_control({**good, "areas": [{"status": 3, "polygons": []}]})
    with pytest.raises(ValueError, match="count"):
        parse_outlines({"outlines": []})


def test_snapshot_bounds_are_enforced() -> None:
    place = SettlementControl(
        1, "P", "O", 48.0, 37.0, ControlStatus.RU, None, (ControlStatus.RU,) * 4
    )  # type: ignore[arg-type]
    base = {
        "assessment_date": date(2026, 9, 2),
        "release_stamp": "v1",
        "retrieved_at": datetime(2026, 9, 13, tzinfo=UTC),
        "attribution": "A",
        "licence": "ODbL",
        "source_url": "u",
        "method_note": "m",
        "places_total": 1,
        "settlements": (place,),
        "areas": (),
        "oblasts": (OblastControl("O", 1, 0, 1, 0, 0),),
        "changes": (),
    }
    assert ControlSnapshot(**base).count(ControlStatus.RU) == 1  # type: ignore[arg-type]
    ring = tuple((float(i), 0.0) for i in range(30_001))
    with pytest.raises(ValueError, match="vertex"):
        ControlSnapshot(**{**base, "areas": (ControlArea(ControlStatus.RU, ((ring,), (ring,))),)})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="settlement count"):
        ControlSnapshot(**{**base, "settlements": ()})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="retain"):
        ControlSnapshot(**{**base, "places_total": 0})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="oblast or change"):
        ControlSnapshot(**{**base, "oblasts": (OblastControl("O", 1, 0, 1, 0, 0),) * 31})  # type: ignore[arg-type]


def test_cli_commands_report_success_and_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = CliRunner()
    monkeypatch.setattr("ase.cli_ukraine.import_ukraine_control", lambda d, contact: 7)
    monkeypatch.setattr("ase.cli_ukraine.import_ukraine_oblasts", lambda d, contact: 27)
    result = runner.invoke(
        app, ["import-ukraine-control", "--destination", str(tmp_path / "c.json")]
    )
    assert result.exit_code == 0 and "7 frontline-zone settlements" in result.output
    result = runner.invoke(
        app, ["import-ukraine-oblasts", "--destination", str(tmp_path / "o.json")]
    )
    assert result.exit_code == 0 and "27 oblast outlines" in result.output

    def explode(d: str, contact: str) -> int:
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("ase.cli_ukraine.import_ukraine_control", explode)
    monkeypatch.setattr("ase.cli_ukraine.import_ukraine_oblasts", explode)
    for command in ("import-ukraine-control", "import-ukraine-oblasts"):
        result = runner.invoke(app, [command, "--destination", str(tmp_path / "x.json")])
        assert result.exit_code == 1 and "ConnectError" in result.output
