"""Operator-run imports of public infrastructure snapshots: ground stations and data centres.

Both run only from the CLI. Ground stations come from Wikidata (CC0) and are merged
behind the curated list already in the snapshot; data centres come from OpenStreetMap
via Overpass (ODbL, attributed). Neither establishes operational status.
"""

from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from ase.adapters.geo.countries import CountryIndex, load_records

SPARQL = "https://query.wikidata.org/sparql"
OVERPASS = "https://overpass-api.de/api/interpreter"
DEFAULT_CONTACT = "https://github.com/ShabalalaWATP/OSINT"
MAX_STATIONS = 500
MAX_CENTRES = 3_600
NEAR_DEGREES = 0.05
STATION_CLASSES = ("Q1349167", "Q10379228")  # ground station, teleport
STATION_QUERY = (
    "SELECT ?item ?itemLabel ?coord ?operatorLabel ?iso ?site ?web WHERE { "
    "VALUES ?class { " + " ".join(f"wd:{q}" for q in STATION_CLASSES) + " } "
    "?item wdt:P31 ?class ; wdt:P625 ?coord . FILTER NOT EXISTS { ?item wdt:P576 ?closed } "
    "OPTIONAL { ?item wdt:P137 ?operator } "
    "OPTIONAL { ?item wdt:P17 ?country . ?country wdt:P297 ?iso } "
    "OPTIONAL { ?site schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> } "
    "OPTIONAL { ?item wdt:P856 ?web } "
    'SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". } }'
)
CENTRE_QUERY = '[out:json][timeout:180];nwr["telecom"="data_center"]["name"];out center tags;'


def _agent(contact: str) -> str:
    return f"TheAllSeeingEye/0.1 ({contact}; operator-run infrastructure import) httpx"


def _point(value: str | None) -> tuple[float, float] | None:
    match = re.fullmatch(r"Point\(([-0-9.]+) ([-0-9.]+)\)", value or "")
    return (float(match.group(1)), float(match.group(2))) if match else None


def _https(value: str | None) -> str | None:
    return value if value and value.startswith("https://") and len(value) <= 300 else None


def _clean(value: str | None, limit: int = 120) -> str:
    return " ".join((value or "").split())[:limit]


def parse_station_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One station per item; the first operator row wins, items without a country are skipped."""
    stations: dict[str, dict[str, Any]] = {}
    for row in rows:
        qid = str(row.get("item", "")).rsplit("/", 1)[-1]
        point = _point(row.get("coord"))
        iso = _clean(row.get("iso"), 2).upper()
        name = _clean(row.get("itemLabel"))
        if not qid or point is None or len(iso) != 2 or not name or name == qid:
            continue
        if qid in stations:
            continue
        stations[qid] = {
            "id": f"wd-{qid.lower()}",
            "name": name,
            "operator": _clean(row.get("operatorLabel")) or "Operator not recorded",
            "country": iso,
            "longitude": round(point[0], 4),
            "latitude": round(point[1], 4),
            "source_url": _https(row.get("site")) or f"https://www.wikidata.org/wiki/{qid}",
            "note": (
                "Wikidata item with a recorded coordinate; approximate site location, "
                "not an antenna position or a statement of current use."
            ),
            "website": _https(row.get("web")),
            "wikipedia": _https(row.get("site")),
        }
    return sorted(stations.values(), key=lambda s: (s["country"], s["name"]))


def merge_stations(
    curated: list[dict[str, Any]], imported: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Curated entries keep precedence; imported sites near a curated one are dropped."""
    kept = list(curated)
    for station in imported:
        near = any(
            abs(station["longitude"] - item["longitude"]) < NEAR_DEGREES
            and abs(station["latitude"] - item["latitude"]) < NEAR_DEGREES
            for item in kept
        )
        if not near:
            kept.append(station)
    return kept[:MAX_STATIONS]


def import_ground_stations(destination: str, contact: str = DEFAULT_CONTACT) -> int:
    with open(destination, encoding="utf-8") as handle:
        existing = json.load(handle)
    curated = [item for item in existing if not str(item.get("id", "")).startswith("wd-")]
    with httpx.Client(timeout=180, headers={"User-Agent": _agent(contact)}) as client:
        response = client.get(
            SPARQL,
            params={"query": STATION_QUERY},
            headers={"Accept": "application/sparql-results+json"},
        )
        if response.status_code == 429:
            time.sleep(min(float(response.headers.get("Retry-After", "30")), 120.0))
            response = client.get(
                SPARQL,
                params={"query": STATION_QUERY},
                headers={"Accept": "application/sparql-results+json"},
            )
        response.raise_for_status()
        bindings = response.json()["results"]["bindings"]
    rows = [{key: value.get("value") for key, value in row.items()} for row in bindings]
    merged = merge_stations(curated, parse_station_rows(rows))
    with open(destination, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(merged, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    return len(merged)


def parse_centre_elements(
    elements: list[dict[str, Any]], index: CountryIndex
) -> list[dict[str, Any]]:
    centres: list[dict[str, Any]] = []
    for element in elements:
        tags = element.get("tags") or {}
        kind, ident = element.get("type"), element.get("id")
        centre = element.get("center") or element
        lon, lat = centre.get("lon"), centre.get("lat")
        name = _clean(tags.get("name"))
        if kind not in {"node", "way", "relation"} or not isinstance(ident, int) or not name:
            continue
        if not isinstance(lon, int | float) or not isinstance(lat, int | float):
            continue
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            continue
        centres.append(
            {
                "id": f"osm-{kind}-{ident}",
                "name": name,
                "operator": _clean(tags.get("operator") or tags.get("brand"))
                or "Operator not recorded",
                "country": index.resolve(float(lon), float(lat)),
                "longitude": round(float(lon), 4),
                "latitude": round(float(lat), 4),
                "website": _https(tags.get("website") or tags.get("contact:website")),
                "source_url": f"https://www.openstreetmap.org/{kind}/{ident}",
                "note": "Mapped position only; not capacity, tenants or current operation.",
            }
        )
    centres.sort(key=lambda c: (c["country"] or "ZZ", c["name"], c["id"]))
    return centres[:MAX_CENTRES]


def import_data_centres(destination: str, contact: str = DEFAULT_CONTACT) -> int:
    with httpx.Client(timeout=240, headers={"User-Agent": _agent(contact)}) as client:
        response = client.post(OVERPASS, data={"data": CENTRE_QUERY})
        response.raise_for_status()
        payload = response.json()
    elements = payload.get("elements")
    if not isinstance(elements, list) or len(elements) > 20_000:
        raise ValueError("Unexpected Overpass result shape")
    items = parse_centre_elements(elements, CountryIndex(load_records()))
    snapshot = {
        "attribution": (
            "© OpenStreetMap contributors (ODbL). Features tagged telecom=data_center with a "
            "name; coverage is incomplete and uneven between countries."
        ),
        "licence_url": "https://www.openstreetmap.org/copyright",
        "snapshot_date": datetime.now(UTC).date().isoformat(),
        "_provenance": {
            "source_url": OVERPASS,
            "query": CENTRE_QUERY,
            "osm_base": str(payload.get("osm3s", {}).get("timestamp_osm_base", "")),
        },
        "items": items,
    }
    with open(destination, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(snapshot, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    return len(items)
