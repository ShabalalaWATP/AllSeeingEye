"""Operator-run imports of the energy and semiconductor site layers.

Curated key sites (repository JSON) are resolved through Wikidata's entity API for a
coordinate, operator, owner, description and links; OpenStreetMap supplies breadth.
Curated entries keep precedence and a stated significance. Nothing here verifies
current operation, output or ownership; every site carries that note.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from importlib.resources import files
from typing import Any

import httpx

from ase.adapters.geo.countries import CountryIndex, load_records
from ase.adapters.geo.sites_osm import (
    ENERGY_QUERIES,
    NOTE,
    OVERPASS,
    SEMICONDUCTOR_QUERIES,
    osm_sites,
)
from ase.adapters.wikidata_entities import DEFAULT_CONTACT, EntityFacts, WikidataEntities

MAX_SITES = {"energy": 3_200, "semiconductor": 300}
NEAR_DEGREES = 0.02
ENERGY_WORDS = (
    "refiner",
    "oil",
    "gas",
    "terminal",
    "field",
    "pipeline",
    "port",
    "lng",
    "storage",
    "hub",
    "petrol",
)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:50]


def choose_hit(
    hits: list[tuple[str, str, str]], match: str | None, words: tuple[str, ...]
) -> str | None:
    """Prefer a hit whose label or description holds the seed's match word, then a domain word."""
    for qid, label, description in hits:
        haystack = f"{label} {description}".lower()
        if match and match.lower() in haystack:
            return qid
    if match:
        return None
    for qid, label, description in hits:
        haystack = f"{label} {description}".lower()
        if any(word in haystack for word in words):
            return qid
    return hits[0][0] if hits else None


def company_links(seed: dict[str, Any], entities: WikidataEntities) -> list[dict[str, str]]:
    """Website and article of the operating company named in the seed, when Wikidata has them."""
    label = seed.get("company_search")
    if not label:
        return []
    qid = choose_hit(entities.search(str(label)), None, ("company", "manufacturer", "corporation"))
    facts = entities.facts([qid]).get(qid) if qid else None
    if facts is None:
        return []
    links = []
    if facts.website:
        links.append({"label": f"{facts.label or label} website", "url": facts.website})
    if facts.wikipedia:
        links.append({"label": f"{facts.label or label} on Wikipedia", "url": facts.wikipedia})
    return links


def site_links(site: dict[str, Any]) -> list[dict[str, str]]:
    """Links in display order: article, site website, then the source record."""
    links = []
    if site.get("wikipedia"):
        links.append({"label": "Wikipedia", "url": site["wikipedia"]})
    if site.get("website"):
        links.append({"label": "Site website", "url": site["website"]})
    for link in site.get("links") or []:
        if link["url"] not in {known["url"] for known in links}:
            links.append(link)
    source = site.get("source_url") or ""
    if source.startswith("https://www.openstreetmap.org/"):
        links.append({"label": "OpenStreetMap feature", "url": source})
    elif source.startswith("https://www.wikidata.org/wiki/"):
        links.append({"label": "Wikidata", "url": source})
    return links[:6]


def resolve_seed(
    seed: dict[str, Any], entities: WikidataEntities, words: tuple[str, ...]
) -> dict[str, Any] | None:
    """A curated site with a Wikidata coordinate, or the seed's city as a city-level fallback."""
    qid = choose_hit(entities.search(str(seed["search"])), seed.get("match"), words)
    facts: EntityFacts | None = entities.facts([qid]).get(qid) if qid else None
    coords, precision = (facts.coords if facts else None), "site"
    if coords is None and seed.get("city"):
        city_qid = choose_hit(entities.search(str(seed["city"])), None, ("city", "town", "capital"))
        city = entities.facts([city_qid]).get(city_qid) if city_qid else None
        coords, precision = (city.coords if city else None), "city"
    if coords is None:
        return None
    name = facts.label if facts and facts.label and precision == "site" else str(seed["search"])
    operator = (facts.operators[0] if facts and facts.operators else None) or seed.get("company")
    return {
        "id": f"wd-{qid.lower()}" if qid and precision == "site" else f"seed-{_slug(name)}",
        "kind": str(seed["kind"]),
        "name": name,
        "operator": operator or "Operator not recorded",
        "owner": ", ".join(facts.owners) if facts and facts.owners else None,
        "country": str(seed["country"]),
        "longitude": round(coords[0], 4),
        "latitude": round(coords[1], 4),
        "precision": precision,
        "description": (facts.description if facts and precision == "site" else None) or None,
        "significance": str(seed.get("significance") or ""),
        "detail": str(seed.get("detail") or "") or None,
        "links": company_links(seed, entities),
        "website": facts.website if facts and precision == "site" else None,
        "wikipedia": facts.wikipedia if facts and precision == "site" else None,
        "wikidata": qid if precision == "site" else None,
        "source_url": (
            f"https://www.wikidata.org/wiki/{qid}" if qid and precision == "site" else ""
        )
        or "https://www.wikidata.org/",
        "note": NOTE
        if precision == "site"
        else "Placed at the city named in the curated entry; the site itself is not geolocated. "
        + NOTE,
    }


def merge_sites(
    curated: list[dict[str, Any]], mapped: list[dict[str, Any]], bound: int
) -> list[dict[str, Any]]:
    kept = list(curated)
    for site in mapped:
        near = any(
            abs(site["longitude"] - item["longitude"]) < NEAR_DEGREES
            and abs(site["latitude"] - item["latitude"]) < NEAR_DEGREES
            for item in curated
        )
        if not near:
            kept.append(site)
    kept.sort(key=lambda s: (not s.get("significance"), s.get("country") or "ZZ", s["name"]))
    return kept[:bound]


def _seeds(name: str) -> list[dict[str, Any]]:
    items = json.loads(files("ase.resources").joinpath(name).read_text("utf-8"))
    if not isinstance(items, list) or len(items) > 200:
        raise ValueError("Curated site seeds must be a bounded list")
    return items


def previous_mapped(destination: str | None) -> list[dict[str, Any]]:
    """OpenStreetMap items from the last snapshot, kept when Overpass cannot answer."""
    if not destination:
        return []
    try:
        with open(destination, encoding="utf-8") as handle:
            items = json.load(handle).get("items", [])
    except (OSError, ValueError):
        return []
    mapped = [item for item in items if str(item.get("id", "")).startswith("osm-")]
    for item in mapped:
        for key in ("owner", "description", "significance", "detail", "wikipedia", "wikidata"):
            item.setdefault(key, None)
        item.setdefault("precision", "mapped")
        item.setdefault("links", [])
    return mapped


def build_layer(layer: str, contact: str, destination: str | None = None) -> dict[str, Any]:
    seeds = _seeds(f"{layer}_key_sites.json")
    words = ENERGY_WORDS if layer == "energy" else ("semiconductor", "fab", "chip", "company")
    entities = WikidataEntities.open(contact)
    curated: list[dict[str, Any]] = []
    unresolved: list[str] = []
    try:
        for seed in seeds:
            try:
                site = resolve_seed(seed, entities, words)
            except httpx.HTTPError:
                site = None  # a dropped lookup leaves the seed unresolved, not the run failed
            if site is None:
                unresolved.append(str(seed["search"]))
            else:
                curated.append(site)
    finally:
        entities.close()
    agent = f"TheAllSeeingEye/0.1 ({contact}; operator-run infrastructure import) httpx"
    index = CountryIndex(load_records())
    queries = ENERGY_QUERIES if layer == "energy" else SEMICONDUCTOR_QUERIES
    try:
        with httpx.Client(timeout=300, headers={"User-Agent": agent}) as client:
            mapped = osm_sites(client, queries, index)
    except httpx.HTTPError:
        mapped = previous_mapped(destination)  # Overpass down: keep the last mapped breadth
        if not mapped:
            raise
    items = merge_sites(curated, mapped, MAX_SITES[layer])
    for item in items:
        item["links"] = site_links(item)
        item.setdefault("detail", None)
    return {
        "attribution": (
            "Curated key sites resolved through Wikidata (CC0); breadth from © OpenStreetMap "
            "contributors (ODbL). Coverage is incomplete and uneven between countries."
        ),
        "licence_url": "https://www.openstreetmap.org/copyright",
        "snapshot_date": datetime.now(UTC).date().isoformat(),
        "_provenance": {
            "overpass": OVERPASS,
            "seeds": f"{layer}_key_sites.json",
            "curated": len(curated),
            "unresolved": unresolved,
        },
        "items": items,
    }


def import_sites(layer: str, destination: str, contact: str = DEFAULT_CONTACT) -> int:
    if layer not in MAX_SITES:
        raise ValueError("Unknown site layer")
    snapshot = build_layer(layer, contact, destination)
    with open(destination, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(snapshot, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    return len(snapshot["items"])
