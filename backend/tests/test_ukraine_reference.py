"""Ukraine reference notes: bounded catalogue, seed resolution with fakes, images by id."""

from __future__ import annotations

import io
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from httpx import AsyncClient
from PIL import Image

from ase.adapters.geo import ukraine_reference_import as importer
from ase.adapters.geo.ukraine_reference import (
    load_reference_catalogue,
    load_reference_image,
    parse_catalogue,
)
from ase.adapters.wikidata_entities import EntityFacts
from ase.domain.ukraine.reference import (
    SPECIALITIES,
    TIMELINE_THEMES,
    EquipmentEntry,
    ForceNode,
    ReferenceCatalogue,
    Side,
    TimelineEvent,
    TimelinePhase,
)
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token

SEED_FILES = (
    "ukraine_equipment_seeds.json",
    "ukraine_forces_seeds.json",
    "ukraine_timeline_seeds.json",
)


def test_seed_files_are_complete_and_dated() -> None:
    equipment, forces, timeline = (importer.read_seeds(name) for name in SEED_FILES)
    for item in equipment["items"]:
        assert item["group"] in SPECIALITIES and item["subgroup"] in SPECIALITIES[item["group"]][1]
        assert item["side"] in ("ru", "ua") and date.fromisoformat(item["as_of"])
        assert 40 < len(item["description"]) <= 900 and item["search"]
    ids = {item["id"] for item in forces["items"]}
    for node in forces["items"]:
        assert node["parent_id"] is None or node["parent_id"] in ids
        assert date.fromisoformat(node["as_of"]) and node["role"]
    phases = {phase["id"] for phase in timeline["phases"]}
    for event in timeline["events"]:
        assert event["phase_id"] in phases and event["theme"] in TIMELINE_THEMES
        assert date.fromisoformat(event["on"]) and 40 < len(event["text"]) <= 900
    assert {"ru", "ua"} == {item["side"] for item in equipment["items"]}


def test_packaged_catalogue_loads_with_links_dates_and_licensed_images() -> None:
    catalogue = load_reference_catalogue()
    assert catalogue is not None
    assert catalogue.equipment and catalogue.forces and catalogue.events and catalogue.phases
    assert all(entry.links and entry.as_of.year >= 2025 for entry in catalogue.equipment)
    assert all(node.as_of.year >= 2025 for node in catalogue.forces)
    with_image = [e for e in catalogue.equipment if e.image_id]
    assert len(with_image) >= len(catalogue.equipment) // 2
    for entry in with_image:
        image = catalogue.images[entry.image_id or ""]
        assert image.licence and image.credit and image.source_url.startswith("https://commons")
        assert load_reference_image(entry.image_id or "") is not None
    assert load_reference_image("../etc/passwd") is None
    assert load_reference_image("no-such-image") is None


class FakeEntities:
    def __init__(self, hits: dict[str, list[tuple[str, str, str]]], facts: dict[str, EntityFacts]):
        self._hits, self._facts = hits, facts

    def search(self, text: str, limit: int = 5) -> list[tuple[str, str, str]]:
        return self._hits.get(text, [])

    def facts(self, qids: list[str]) -> dict[str, EntityFacts]:
        return {qid: self._facts[qid] for qid in qids if qid in self._facts}


def fact(qid: str, label: str, image: str | None) -> EntityFacts:
    return EntityFacts(
        qid=qid,
        label=label,
        description="",
        coords=None,
        operators=(),
        owners=(),
        country=None,
        website=None,
        wikipedia=f"https://en.wikipedia.org/wiki/{label.replace(' ', '_')}",
        image=image,
    )


def no_article(qid: str) -> EntityFacts:
    base = fact(qid, "Bare", None)
    return EntityFacts(**{**{f: getattr(base, f) for f in base.__slots__}, "wikipedia": None})


def jpeg_bytes(width: int = 900, height: int = 600) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (120, 80, 40)).save(buffer, format="JPEG")
    return buffer.getvalue()


def commons_client(licence: str | None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if "api.php" in str(request.url):
            meta = {"Artist": {"value": "<a href='x'>Someone</a>"}}
            if licence:
                meta["LicenseShortName"] = {"value": licence}
            return httpx.Response(
                200, json={"query": {"pages": {"1": {"imageinfo": [{"extmetadata": meta}]}}}}
            )
        return httpx.Response(200, content=jpeg_bytes())

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_resolve_entries_adds_ids_articles_and_bounded_images(tmp_path: Path) -> None:
    entities = FakeEntities(
        {"T-90M": [("Q1", "T-90M", "tank")], "Nothing": [("Q9", "Unrelated thing", "")]},
        {"Q1": fact("Q1", "T-90M", "T-90M.jpg"), "Q2": no_article("Q2")},
    )
    items: list[dict[str, Any]] = [
        {"id": "ru-t-90m", "search": "T-90M", "links": [{"label": "Oryx", "url": "https://x"}]},
        {"id": "ru-mystery", "search": "Nothing"},
        {"id": "ru-fixed", "wikidata_id": "Q1"},
        {"id": "ru-bare", "wikidata_id": "Q2"},
    ]
    images: dict[str, Any] = {}
    with commons_client("CC BY-SA 4.0") as client:
        resolved = importer.resolve_entries(
            items,
            entities,  # type: ignore[arg-type]
            client,
            tmp_path,
            images,
            True,
        )
    assert resolved[0]["wikidata_id"] == "Q1" and resolved[0]["image_id"] == "ru-t-90m"
    assert [link["label"] for link in resolved[0]["links"]] == ["Oryx", "Wikipedia article"]
    assert resolved[1]["wikidata_id"] is None and resolved[1]["image_id"] is None
    assert resolved[2]["wikidata_id"] == "Q1"
    assert resolved[3]["links"] == [
        {"label": "Wikidata item", "url": "https://www.wikidata.org/wiki/Q2"}
    ]
    image = images["ru-t-90m"]
    assert image["licence"] == "CC BY-SA 4.0" and image["credit"] == "Someone"
    assert image["width"] == 480 and image["bytes"] <= 60_000
    assert (tmp_path / "ru-t-90m.jpg").stat().st_size == image["bytes"]
    with commons_client(None) as client:
        assert importer.cache_image(client, "x.jpg", tmp_path / "x.jpg") is None


def test_import_writes_a_catalogue_from_seeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entities = FakeEntities({}, {})
    monkeypatch.setattr(importer.WikidataEntities, "open", classmethod(lambda cls, c: entities))
    monkeypatch.setattr(entities, "close", lambda: None, raising=False)
    destination = tmp_path / "ukraine_reference.json"
    count = importer.import_ukraine_reference(str(destination))
    catalogue = parse_catalogue(json.loads(destination.read_text("utf-8")))
    assert count == len(catalogue.equipment) + len(catalogue.forces) + len(catalogue.events)
    assert not catalogue.images and (tmp_path / "ukraine_images").is_dir()


def catalogue_kwargs(**overrides: Any) -> dict[str, Any]:
    phase = TimelinePhase("p", "Phase", date(2022, 2, 24), None, "Summary")
    base: dict[str, Any] = {
        "retrieved_at": datetime(2026, 9, 13, tzinfo=UTC),
        "source_note": "note",
        "equipment": (
            EquipmentEntry(
                "e",
                Side.RU,
                "tanks",
                "main_battle",
                "T",
                "RU",
                "role",
                "d",
                None,
                None,
                None,
                date(2026, 6, 30),
                (),
            ),
        ),
        "forces": (
            ForceNode("f", Side.UA, None, "N", "r", None, None, None, None, date(2026, 6, 30), ()),
        ),
        "phases": (phase,),
        "events": (
            TimelineEvent("ev", "p", date(2022, 2, 24), "T", "t", "ground", None, None, ()),
        ),
        "images": {},
    }
    return {**base, **overrides}


def test_catalogue_validation_catches_broken_references() -> None:
    ReferenceCatalogue(**catalogue_kwargs())
    bad_parent = ForceNode(
        "f", Side.UA, "missing", "N", "r", None, None, None, None, date(2026, 1, 1), ()
    )
    with pytest.raises(ValueError, match="parent"):
        ReferenceCatalogue(**catalogue_kwargs(forces=(bad_parent,)))
    orphan = TimelineEvent("ev", "nope", date(2022, 2, 24), "T", "t", "ground", None, None, ())
    with pytest.raises(ValueError, match="phase"):
        ReferenceCatalogue(**catalogue_kwargs(events=(orphan,)))
    odd_theme = TimelineEvent("ev", "p", date(2022, 2, 24), "T", "t", "weather", None, None, ())
    with pytest.raises(ValueError, match="theme"):
        ReferenceCatalogue(**catalogue_kwargs(events=(odd_theme,)))
    odd_group = EquipmentEntry(
        "e", Side.RU, "boats", "x", "T", "RU", "role", "d", None, None, None, date(2026, 6, 30), ()
    )
    with pytest.raises(ValueError, match="speciality"):
        ReferenceCatalogue(**catalogue_kwargs(equipment=(odd_group,)))
    with_image = EquipmentEntry(
        "e",
        Side.RU,
        "tanks",
        "main_battle",
        "T",
        "RU",
        "role",
        "d",
        None,
        None,
        "img",
        date(2026, 6, 30),
        (),
    )
    with pytest.raises(ValueError, match="manifest"):
        ReferenceCatalogue(**catalogue_kwargs(equipment=(with_image,)))
    duplicate = ForceNode(
        "e", Side.UA, None, "N", "r", None, None, None, None, date(2026, 1, 1), ()
    )
    with pytest.raises(ValueError, match="unique"):
        ReferenceCatalogue(**catalogue_kwargs(forces=(duplicate,)))


def test_loader_rejects_bad_ids_links_and_sizes() -> None:
    raw = {
        "retrieved_at": "2026-09-13T00:00:00+00:00",
        "source_note": "n",
        "equipment": [],
        "forces": [],
        "phases": [],
        "events": [],
        "images": {
            "a": {"licence": "CC0", "credit": "c", "source_url": "https://x", "bytes": 70000}
        },
    }
    with pytest.raises(ValueError, match="byte"):
        parse_catalogue(raw)
    entry = {
        "id": "e",
        "side": "ru",
        "group": "tanks",
        "subgroup": "main_battle",
        "name": "T",
        "origin": "RU",
        "role": "r",
        "description": "d",
        "as_of": "2026-06-30",
    }
    for bad in (
        {"wikidata_id": "X1"},
        {"image_id": "Bad Id"},
        {"links": [{"label": "l", "url": "http://x"}]},
    ):
        with pytest.raises(ValueError):
            parse_catalogue({**raw, "images": {}, "equipment": [{**entry, **bad}]})


async def test_reference_endpoints_serve_the_catalogue_and_images(
    client: AsyncClient, user: User
) -> None:
    assert (await client.get("/api/conflicts/ukraine/reference")).status_code == 401
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.get("/api/conflicts/ukraine/reference", headers=bearer(token))
    assert response.status_code == 200
    body = response.json()
    assert body["specialities"][0]["key"] == "drones" and "ground" in body["themes"]
    assert len(body["equipment"]) > 80 and len(body["forces"]) > 20 and len(body["events"]) > 30
    entry = next(e for e in body["equipment"] if e["image_id"])
    image = await client.get(
        f"/api/conflicts/ukraine/images/{entry['image_id']}.jpg", headers=bearer(token)
    )
    assert image.status_code == 200 and image.headers["content-type"] == "image/jpeg"
    assert image.headers["cache-control"] == "private, max-age=86400"
    assert image.content[:2] == b"\xff\xd8"
    missing = await client.get("/api/conflicts/ukraine/images/nothing.jpg", headers=bearer(token))
    assert missing.status_code == 404
