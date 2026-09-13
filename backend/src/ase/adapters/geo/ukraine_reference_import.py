"""Resolve the hand-written Ukraine reference seeds through Wikidata and cache licensed images.

Seeds carry the text, links and as-of dates. Wikidata adds the identifier, the article and
the Commons image name; Commons adds the licence and credit; the image itself is re-encoded
as a small JPEG. Operator-run, never at runtime.
"""

from __future__ import annotations

import html
import io
import json
import re
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

import httpx
from PIL import Image

from ase.adapters.wikidata_entities import DEFAULT_CONTACT, EntityFacts, WikidataEntities
from ase.domain.ukraine.reference import MAX_IMAGE_BYTES

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
IMAGE_WIDTH = 480
MAX_DOWNLOAD_BYTES = 4_000_000
SEEDS = ("ukraine_equipment_seeds.json", "ukraine_forces_seeds.json", "ukraine_timeline_seeds.json")
SOURCE_NOTE = (
    "Hand-written reference notes with a source link and an as-of date on every entry, "
    "resolved through Wikidata for identifiers and articles; images are Wikimedia Commons "
    "files with their licence and credit. Background, not intelligence."
)


def _plain(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", "", value)).split())[:300]


def read_seeds(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(files("ase.resources").joinpath(name).read_text("utf-8"))
    return data


def pick_entity(entities: WikidataEntities, seed: dict[str, Any]) -> str | None:
    """An explicit QID wins; otherwise the first search hit whose label shares a word."""
    if qid := seed.get("wikidata_id"):
        return str(qid)
    search = seed.get("search")
    if not search:
        return None
    words = {w.lower() for w in re.findall(r"[\w-]{3,}", str(search))}
    for qid, label, _description in entities.search(str(search), limit=5):
        if words & {w.lower() for w in re.findall(r"[\w-]{3,}", label)}:
            return qid
    return None


def cache_image(client: httpx.Client, filename: str, destination: Path) -> dict[str, Any] | None:
    """Fetch one Commons file, keep licence and credit, write a bounded JPEG; None if unusable."""
    name = unquote(filename.rsplit("/", 1)[-1])
    info = client.get(
        COMMONS_API,
        params={
            "action": "query",
            "titles": f"File:{name}",
            "prop": "imageinfo",
            "iiprop": "extmetadata",
            "format": "json",
        },
    )
    info.raise_for_status()
    pages: dict[str, Any] = info.json().get("query", {}).get("pages", {})
    page: dict[str, Any] = next(iter(pages.values()), {})
    infos: list[dict[str, Any]] = page.get("imageinfo") or [{}]
    meta: dict[str, Any] = infos[0].get("extmetadata", {})
    licence = _plain(meta.get("LicenseShortName", {}).get("value", ""))
    if not licence:
        return None
    credit = _plain(meta.get("Artist", {}).get("value", "")) or "Wikimedia Commons"
    picture = client.get(
        f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(name)}",
        params={"width": IMAGE_WIDTH},
        follow_redirects=True,
    )
    picture.raise_for_status()
    if len(picture.content) > MAX_DOWNLOAD_BYTES:
        return None
    image = Image.open(io.BytesIO(picture.content)).convert("RGB")
    if image.width > IMAGE_WIDTH:
        image = image.resize(
            (IMAGE_WIDTH, round(image.height * IMAGE_WIDTH / image.width)), Image.Resampling.LANCZOS
        )
    encoded = b""
    for quality in (78, 68, 58, 48):
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
        encoded = buffer.getvalue()
        if len(encoded) <= MAX_IMAGE_BYTES:
            break
    if len(encoded) > MAX_IMAGE_BYTES:
        return None
    destination.write_bytes(encoded)
    return {
        "licence": licence[:80],
        "credit": credit,
        "source_url": f"https://commons.wikimedia.org/wiki/File:{quote(name)}",
        "width": image.width,
        "height": image.height,
        "bytes": len(encoded),
    }


def _links(seed: dict[str, Any], facts: EntityFacts | None) -> list[dict[str, str]]:
    """Seed links, then the article; an item without an article links its Wikidata page."""
    links = [dict(link) for link in seed.get("links") or []]
    if facts and facts.wikipedia and all(link["url"] != facts.wikipedia for link in links):
        links.append({"label": "Wikipedia article", "url": facts.wikipedia})
    elif facts and not links:
        links.append(
            {"label": "Wikidata item", "url": f"https://www.wikidata.org/wiki/{facts.qid}"}
        )
    return links[:8]


def resolve_entries(
    items: list[dict[str, Any]],
    entities: WikidataEntities,
    client: httpx.Client,
    image_folder: Path,
    images: dict[str, Any],
    with_images: bool,
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    qids = {item["id"]: pick_entity(entities, item) for item in items}
    facts = entities.facts([qid for qid in qids.values() if qid])
    for item in items:
        fact = facts.get(qids[item["id"]] or "")
        entry = {k: v for k, v in item.items() if k not in ("search", "links")}
        entry["wikidata_id"] = fact.qid if fact else None
        entry["links"] = _links(item, fact)
        entry["image_id"] = None
        if with_images and fact and fact.image:
            cached = cache_image(client, fact.image, image_folder / f"{item['id']}.jpg")
            if cached is not None:
                images[item["id"]] = cached
                entry["image_id"] = item["id"]
        resolved.append(entry)
    return resolved


def import_ukraine_reference(destination: str, contact: str = DEFAULT_CONTACT) -> int:
    equipment, forces, timeline = (read_seeds(name) for name in SEEDS)
    folder = Path(destination).parent / "ukraine_images"
    folder.mkdir(exist_ok=True)
    images: dict[str, Any] = {}
    entities = WikidataEntities.open(contact)
    agent = f"TheAllSeeingEye/0.1 ({contact}; operator-run reference import) httpx"
    try:
        with httpx.Client(timeout=60, headers={"User-Agent": agent}) as client:
            catalogue = {
                "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "source_note": SOURCE_NOTE,
                "equipment": resolve_entries(
                    equipment["items"], entities, client, folder, images, True
                ),
                "forces": resolve_entries(forces["items"], entities, client, folder, images, False),
                "phases": timeline["phases"],
                "events": resolve_entries(
                    timeline["events"], entities, client, folder, images, True
                ),
                "images": images,
            }
    finally:
        entities.close()
    Path(destination).write_text(
        json.dumps(catalogue, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    return len(catalogue["equipment"]) + len(catalogue["forces"]) + len(catalogue["events"])
