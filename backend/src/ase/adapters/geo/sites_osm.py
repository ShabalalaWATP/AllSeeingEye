"""OpenStreetMap site queries for the energy and semiconductor layers (Overpass, ODbL)."""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import httpx

from ase.adapters.geo.countries import CountryIndex

OVERPASS = "https://overpass-api.de/api/interpreter"
QUERY_PAUSE_SECONDS = 3.0
ENERGY_QUERIES: tuple[tuple[str, str], ...] = (
    ("refinery", '[out:json][timeout:240];nwr["industrial"="refinery"]["name"];out center tags;'),
    (
        "offshore_platform",
        '[out:json][timeout:240];nwr["man_made"="offshore_platform"]["name"];out center tags;',
    ),
    (
        "oil_facility",
        '[out:json][timeout:240];nwr["industrial"="oil"]["name"]["operator"];out center tags;',
    ),
)
SEMICONDUCTOR_QUERIES: tuple[tuple[str, str], ...] = (
    (
        "fab",
        '[out:json][timeout:180];nwr["industrial"="semiconductor"]["name"];out center tags;',
    ),
    (
        "fab",
        '[out:json][timeout:180];nwr["man_made"="works"]["product"~"semiconductor|chips|wafer",i]'
        '["name"];out center tags;',
    ),
)
NOTE = "Mapped position only; ownership, output and current operation are not verified."


def overpass(client: httpx.Client, query: str) -> list[dict[str, Any]]:
    """One query with a polite pause; a busy or rate-limited server is retried once."""
    time.sleep(QUERY_PAUSE_SECONDS)
    response = client.post(OVERPASS, data={"data": query})
    if response.status_code in {429, 502, 503, 504}:
        time.sleep(60.0)
        response = client.post(OVERPASS, data={"data": query})
    response.raise_for_status()
    elements = response.json().get("elements")
    if not isinstance(elements, list) or len(elements) > 20_000:
        raise ValueError("Unexpected Overpass result shape")
    return elements


def _clean(value: Any, limit: int = 120) -> str:
    return " ".join(str(value).split())[:limit] if isinstance(value, str) else ""


def _https(value: Any) -> str | None:
    text = _clean(value, 300)
    return text if text.startswith("https://") else None


def wikipedia_url(tag: Any) -> str | None:
    """OSM stores `wikipedia=en:Title`; only English articles become a link."""
    text = _clean(tag, 200)
    if not text.startswith("en:"):
        return None
    return f"https://en.wikipedia.org/wiki/{quote(text[3:].replace(' ', '_'))}"


def parse_osm_sites(
    elements: list[dict[str, Any]], kind: str, index: CountryIndex
) -> list[dict[str, Any]]:
    sites: list[dict[str, Any]] = []
    for element in elements:
        tags = element.get("tags") or {}
        osm_type, ident = element.get("type"), element.get("id")
        centre = element.get("center") or element
        lon, lat = centre.get("lon"), centre.get("lat")
        name = _clean(tags.get("name:en")) or _clean(tags.get("name"))
        if osm_type not in {"node", "way", "relation"} or not isinstance(ident, int) or not name:
            continue
        if not isinstance(lon, int | float) or not isinstance(lat, int | float):
            continue
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            continue
        wikidata = _clean(tags.get("wikidata"), 20)
        sites.append(
            {
                "id": f"osm-{osm_type}-{ident}",
                "kind": kind,
                "name": name,
                "operator": _clean(tags.get("operator") or tags.get("owner") or tags.get("brand"))
                or "Operator not recorded",
                "owner": _clean(tags.get("owner")) or None,
                "country": index.resolve(float(lon), float(lat)),
                "longitude": round(float(lon), 4),
                "latitude": round(float(lat), 4),
                "precision": "mapped",
                "description": _clean(tags.get("description"), 300) or None,
                "significance": None,
                "website": _https(tags.get("website") or tags.get("contact:website")),
                "wikipedia": wikipedia_url(tags.get("wikipedia")),
                "wikidata": wikidata if wikidata.startswith("Q") else None,
                "source_url": f"https://www.openstreetmap.org/{osm_type}/{ident}",
                "note": NOTE,
            }
        )
    return sites


def osm_sites(
    client: httpx.Client, queries: tuple[tuple[str, str], ...], index: CountryIndex
) -> list[dict[str, Any]]:
    collected: dict[str, dict[str, Any]] = {}
    for kind, query in queries:
        for site in parse_osm_sites(overpass(client, query), kind, index):
            collected.setdefault(site["id"], site)
    return list(collected.values())
