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
from functools import partial
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
MAX_SOURCE_URL = 600  # The catalogue loader rejects anything longer.
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


def commons_url(name: str) -> str | None:
    """The file description page. A percent-encoded Cyrillic title can run past the catalogue's
    URL bound, so fall back to the plain title with the characters that break a URL removed."""
    for candidate in (quote(name), re.sub(r"[\s\"'<>]+", "_", name)):
        url = f"https://commons.wikimedia.org/wiki/File:{candidate}"
        if len(url) <= MAX_SOURCE_URL:
            return url
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
    source_url = commons_url(name)
    if not licence or source_url is None:
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
        "source_url": source_url,
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


def _merge_links(seed: dict[str, Any], previous: dict[str, Any]) -> list[dict[str, str]]:
    """Seed links win; resolved links from the previous run are kept once, without a repeat."""
    links = [dict(link) for link in seed.get("links") or []]
    seen = {link["url"] for link in links}
    for link in previous.get("links") or []:
        if link["url"] not in seen:
            links.append(dict(link))
            seen.add(link["url"])
    return links[:8]


def read_resolved(destination: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Entries and image metadata from a previous run, so a re-import only resolves new items."""
    if not destination.is_file():
        return {}, {}
    raw: dict[str, Any] = json.loads(destination.read_text("utf-8"))
    entries = {
        entry["id"]: entry
        for section in ("equipment", "forces", "events")
        for entry in raw.get(section) or []
    }
    return entries, dict(raw.get("images") or {})


def resolve_entries(
    items: list[dict[str, Any]],
    entities: WikidataEntities,
    client: httpx.Client,
    image_folder: Path,
    images: dict[str, Any],
    with_images: bool,
    known: dict[str, dict[str, Any]] | None = None,
    cached_images: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Resolve each seed; one already resolved with a cached image keeps it instead of refetching.

    A seed may set "image": false when the best Wikidata match is a generic concept whose
    picture would mislead, for example a medieval fort standing in for a 2024 trench line.
    """
    resolved: list[dict[str, Any]] = []
    reused = {
        item["id"]: entry
        for item in items
        if item.get("image") is not False
        and (entry := (known or {}).get(item["id"])) is not None
        and entry.get("image_id") in (cached_images or {})
        and (image_folder / f"{entry['image_id']}.jpg").is_file()
    }
    fresh = [item for item in items if item["id"] not in reused]
    qids = {item["id"]: pick_entity(entities, item) for item in fresh}
    facts = entities.facts([qid for qid in qids.values() if qid])
    for item in items:
        entry = {k: v for k, v in item.items() if k not in ("search", "links", "image")}
        if previous := reused.get(item["id"]):
            entry["wikidata_id"] = previous.get("wikidata_id")
            entry["links"] = _merge_links(item, previous)
            entry["image_id"] = previous["image_id"]
            images[str(entry["image_id"])] = (cached_images or {})[entry["image_id"]]
            resolved.append(entry)
            continue
        fact = facts.get(qids[item["id"]] or "")
        entry["wikidata_id"] = fact.qid if fact else None
        entry["links"] = _links(item, fact)
        entry["image_id"] = None
        if with_images and item.get("image") is not False and fact and fact.image:
            cached = cache_image(client, fact.image, image_folder / f"{item['id']}.jpg")
            if cached is not None:
                images[item["id"]] = cached
                entry["image_id"] = item["id"]
        resolved.append(entry)
    return resolved


def import_ukraine_reference(
    destination: str, contact: str = DEFAULT_CONTACT, reuse: bool = True
) -> int:
    equipment, forces, timeline = (read_seeds(name) for name in SEEDS)
    folder = Path(destination).parent / "ukraine_images"
    folder.mkdir(exist_ok=True)
    known, cached = read_resolved(Path(destination)) if reuse else ({}, {})
    images: dict[str, Any] = {}
    entities = WikidataEntities.open(contact)
    agent = f"TheAllSeeingEye/0.1 ({contact}; operator-run reference import) httpx"
    try:
        with httpx.Client(timeout=60, headers={"User-Agent": agent}) as client:
            resolve = partial(
                resolve_entries,
                entities=entities,
                client=client,
                image_folder=folder,
                images=images,
                known=known,
                cached_images=cached,
            )
            catalogue = {
                "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "source_note": SOURCE_NOTE,
                "equipment": resolve(equipment["items"], with_images=True),
                "forces": resolve(forces["items"], with_images=True),
                "phases": timeline["phases"],
                "events": resolve(timeline["events"], with_images=True),
                "images": images,
            }
    finally:
        entities.close()
    Path(destination).write_text(
        json.dumps(catalogue, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    return len(catalogue["equipment"]) + len(catalogue["forces"]) + len(catalogue["events"])
