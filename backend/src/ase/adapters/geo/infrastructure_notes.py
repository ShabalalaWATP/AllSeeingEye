"""Operator-run enrichment of the packaged cable, nuclear and ground station snapshots.

Cables gain operator, owner, description and links from the OpenStreetMap way tags
and, where a way names a Wikidata item, from that item. Nuclear plants and curated
ground stations are matched to Wikidata by name search within a distance of the
packaged position. Enrichment adds fields; it never moves or removes a record.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from ase.adapters.geo.sites_osm import overpass, wikipedia_url
from ase.adapters.wikidata_entities import DEFAULT_CONTACT, EntityFacts, WikidataEntities

MAX_DISTANCE_DEGREES = 0.5
WAY_BATCH = 200
PLACEHOLDER = "Mapped submarine cable segment"
ENRICHED_FIELDS = ("owner", "description", "website", "wikipedia", "wikidata")
ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii"}


def _clean(value: Any, limit: int = 200) -> str | None:
    text = " ".join(str(value).split())[:limit] if isinstance(value, str) else ""
    return text or None


def _way_ids(cables: list[dict[str, Any]]) -> list[int]:
    ids: list[int] = []
    for cable in cables:
        if cable.get("name") == PLACEHOLDER:
            continue
        match = re.search(r"/way/(\d+)$", str(cable.get("source_url", "")))
        if match:
            ids.append(int(match.group(1)))
    return ids


def cable_tags(client: httpx.Client, way_ids: list[int]) -> dict[int, dict[str, Any]]:
    tags: dict[int, dict[str, Any]] = {}
    for start in range(0, len(way_ids), WAY_BATCH):
        chunk = ",".join(str(i) for i in way_ids[start : start + WAY_BATCH])
        for element in overpass(client, f"[out:json][timeout:120];way(id:{chunk});out tags;"):
            if isinstance(element.get("id"), int):
                tags[element["id"]] = element.get("tags") or {}
    return tags


def enrich_cables(
    cables: list[dict[str, Any]], tags: dict[int, dict[str, Any]], facts: dict[str, EntityFacts]
) -> int:
    """Attach operator, owner, description and links to named segments; count those changed."""
    changed = 0
    for cable in cables:
        match = re.search(r"/way/(\d+)$", str(cable.get("source_url", "")))
        way = tags.get(int(match.group(1))) if match else None
        if not way:
            continue
        item = facts.get(str(way.get("wikidata", "")))
        fields = {
            "operator": _clean(way.get("operator"))
            or (item.operators[0] if item and item.operators else None),
            "owner": _clean(way.get("owner"))
            or (", ".join(item.owners) if item and item.owners else None),
            "description": _clean(way.get("description"), 300)
            or (item.description if item else None),
            "website": _clean(way.get("website"), 300)
            if str(way.get("website", "")).startswith("https://")
            else (item.website if item else None),
            "wikipedia": wikipedia_url(way.get("wikipedia")) or (item.wikipedia if item else None),
            "inception": item.inception if item else None,
        }
        fields = {key: value for key, value in fields.items() if value}
        if fields:
            cable.update(fields)
            changed += 1
    return changed


def _near(a: dict[str, Any], coords: tuple[float, float] | None) -> bool:
    return (
        coords is not None
        and abs(float(a["longitude"]) - coords[0]) <= MAX_DISTANCE_DEGREES
        and abs(float(a["latitude"]) - coords[1]) <= MAX_DISTANCE_DEGREES
    )


def _unit_tokens(name: str) -> set[str]:
    """Numbers and roman numerals in a name distinguish units of one site (Atucha I, II)."""
    return {t for t in re.split(r"[^a-z0-9]+", name.lower()) if t.isdigit() or t in ROMAN}


def label_fits(name: str, label: str) -> bool:
    """The label must share the name's first word and every unit number the name carries."""
    words = [t for t in re.split(r"[^a-z0-9]+", name.lower()) if len(t) >= 3]
    label_tokens = set(re.split(r"[^a-z0-9]+", label.lower()))
    if words and words[0] not in label_tokens:
        return False
    return _unit_tokens(name) <= label_tokens


def match_site(
    entities: WikidataEntities, record: dict[str, Any], words: tuple[str, ...]
) -> EntityFacts | None:
    """First search hit that fits the name, reads like the right kind and sits near the point."""
    hits = entities.search(
        f"{record['name']} {record.get('country', '')}".strip()
    ) or entities.search(str(record["name"]))
    for qid, label, description in hits:
        haystack = f"{label} {description}".lower()
        if not any(word in haystack for word in words) or not label_fits(record["name"], label):
            continue
        facts = entities.facts([qid]).get(qid)
        if facts and _near(record, facts.coords):
            return facts
    return None


def enrich_records(
    records: list[dict[str, Any]], entities: WikidataEntities, words: tuple[str, ...]
) -> int:
    changed = 0
    for record in records:
        if str(record.get("id", "")).startswith("wd-"):
            continue  # imported from Wikidata already; nothing to add
        for key in ENRICHED_FIELDS:
            record.pop(key, None)  # re-runs replace earlier enrichment rather than freezing it
        facts = match_site(entities, record, words)
        if facts is None:
            continue
        fields = {
            "owner": ", ".join(facts.owners) or None,
            "description": facts.description or None,
            "website": facts.website,
            "wikipedia": facts.wikipedia,
            "wikidata": facts.qid,
        }
        if not record.get("operator") and facts.operators:
            fields["operator"] = facts.operators[0]
        record.update({key: value for key, value in fields.items() if value})
        changed += 1
    return changed


def import_infrastructure_notes(resources: str, contact: str = DEFAULT_CONTACT) -> dict[str, int]:
    agent = f"TheAllSeeingEye/0.1 ({contact}; operator-run infrastructure import) httpx"
    counts: dict[str, int] = {}
    cables_path = f"{resources}/submarine_cables.json"
    with open(cables_path, encoding="utf-8") as handle:
        cables = json.load(handle)
    with httpx.Client(timeout=200, headers={"User-Agent": agent}) as client:
        tags = cable_tags(client, _way_ids(cables))
    entities = WikidataEntities.open(contact)
    try:
        qids = sorted(
            {
                str(t["wikidata"])
                for t in tags.values()
                if str(t.get("wikidata", "")).startswith("Q")
            }
        )
        counts["cables"] = enrich_cables(cables, tags, entities.facts(qids))
        nuclear_path = f"{resources}/nuclear_facilities.json"
        with open(nuclear_path, encoding="utf-8") as handle:
            nuclear = json.load(handle)
        counts["nuclear"] = enrich_records(
            nuclear["nuclear_facilities"], entities, ("nuclear", "power station", "power plant")
        )
        stations_path = f"{resources}/ground_stations.json"
        with open(stations_path, encoding="utf-8") as handle:
            stations = json.load(handle)
        counts["stations"] = enrich_records(
            stations, entities, ("station", "antenna", "space", "satellite", "tracking", "teleport")
        )
    finally:
        entities.close()
    for path, data in ((cables_path, cables), (nuclear_path, nuclear), (stations_path, stations)):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=1)
            handle.write("\n")
    return counts
