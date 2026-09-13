"""Operator-run import of reference notes from Wikidata, merged with curated aircraft types.

Ships are Wikidata items with an MMSI and an English Wikipedia article; aircraft are
items with a civil registration and an article. Curated aircraft type notes live in
``reference_aircraft_types.json`` and are copied through unchanged.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from importlib.resources import files
from typing import Any

import httpx

SPARQL = "https://query.wikidata.org/sparql"
DEFAULT_CONTACT = "https://github.com/ShabalalaWATP/OSINT"
LABEL = 'SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". }'
ENWIKI = "?site schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . "
VESSEL_QUERY = (
    "SELECT ?item ?itemLabel ?desc ?mmsi ?imo ?iso ?typeLabel ?site WHERE { "
    "?item wdt:P587 ?mmsi . " + ENWIKI + "OPTIONAL { ?item wdt:P458 ?imo } "
    "OPTIONAL { ?item wdt:P17 ?country . ?country wdt:P297 ?iso } "
    "OPTIONAL { ?item wdt:P31 ?type } "
    'OPTIONAL { ?item schema:description ?desc FILTER(LANG(?desc) = "en") } ' + LABEL + " }"
)
AIRCRAFT_QUERY = (
    "SELECT ?item ?itemLabel ?desc ?reg ?operatorLabel ?site WHERE { "
    "?item wdt:P426 ?reg . " + ENWIKI + "OPTIONAL { ?item wdt:P137 ?operator } "
    'OPTIONAL { ?item schema:description ?desc FILTER(LANG(?desc) = "en") } ' + LABEL + " }"
)
MAX_VESSELS = 4_000
MAX_AIRCRAFT = 1_000


def _sparql(client: httpx.Client, query: str) -> list[dict[str, Any]]:
    headers = {"Accept": "application/sparql-results+json"}
    response = client.get(SPARQL, params={"query": query}, headers=headers)
    if response.status_code == 429:
        time.sleep(min(float(response.headers.get("Retry-After", "30")), 120.0))
        response = client.get(SPARQL, params={"query": query}, headers=headers)
    response.raise_for_status()
    rows = response.json()["results"]["bindings"]
    if not isinstance(rows, list) or len(rows) > 50_000:
        raise ValueError("Unexpected SPARQL result shape")
    return [{key: value.get("value") for key, value in row.items()} for row in rows]


def _qid(uri: str | None) -> str:
    return (uri or "").rsplit("/", 1)[-1]


def _links(site: str | None, qid: str) -> list[dict[str, str]]:
    links = [{"label": "Wikidata", "url": f"https://www.wikidata.org/wiki/{qid}"}]
    if site and site.startswith("https://en.wikipedia.org/"):
        links.insert(0, {"label": "Wikipedia", "url": site})
    return links


def parse_vessels(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One note per MMSI; the first row's type label is kept, others are ignored."""
    vessels: dict[str, dict[str, Any]] = {}
    for row in rows:
        mmsi = str(row.get("mmsi") or "").strip()
        qid = _qid(row.get("item"))
        name = str(row.get("itemLabel") or "").strip()
        if not mmsi.isdigit() or len(mmsi) != 9 or not name or name == qid or mmsi in vessels:
            continue
        parts = [row.get("typeLabel") or "", f"flag {row['iso']}" if row.get("iso") else ""]
        if row.get("imo"):
            parts.append(f"IMO {row['imo']}")
        vessels[mmsi] = {
            "key": mmsi,
            "name": name,
            "description": str(row.get("desc") or "").strip(),
            "detail": " · ".join(p for p in parts if p),
            "links": _links(row.get("site"), qid),
        }
    return sorted(vessels.values(), key=lambda v: v["key"])[:MAX_VESSELS]


def parse_aircraft(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aircraft: dict[str, dict[str, Any]] = {}
    for row in rows:
        reg = str(row.get("reg") or "").strip()
        qid = _qid(row.get("item"))
        name = str(row.get("itemLabel") or "").strip()
        if not 2 <= len(reg) <= 12 or not name or name == qid or reg in aircraft:
            continue
        aircraft[reg] = {
            "key": reg,
            "name": name,
            "description": str(row.get("desc") or "").strip(),
            "detail": str(row.get("operatorLabel") or "").strip(),
            "links": _links(row.get("site"), qid),
        }
    return sorted(aircraft.values(), key=lambda a: a["key"])[:MAX_AIRCRAFT]


def curated_aircraft_types() -> list[dict[str, Any]]:
    text = files("ase.resources").joinpath("reference_aircraft_types.json").read_text("utf-8")
    items = json.loads(text)
    if not isinstance(items, list):
        raise ValueError("Curated aircraft types must be a list")
    return items


def import_reference(destination: str, contact: str = DEFAULT_CONTACT) -> dict[str, int]:
    agent = f"TheAllSeeingEye/0.1 ({contact}; operator-run reference import) httpx"
    with httpx.Client(timeout=240, headers={"User-Agent": agent}) as client:
        vessels = parse_vessels(_sparql(client, VESSEL_QUERY))
        time.sleep(2.0)
        aircraft = parse_aircraft(_sparql(client, AIRCRAFT_QUERY))
    types = curated_aircraft_types()
    snapshot = {
        "schema_version": 1,
        "source": (
            "Wikidata (CC0) via the public SPARQL endpoint for ships and aircraft; curated "
            "ICAO type notes maintained in the repository"
        ),
        "retrieved_at": datetime.now(UTC).isoformat(),
        "vessel": vessels,
        "aircraft": aircraft,
        "aircraft_type": types,
    }
    with open(destination, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(snapshot, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    return {"vessel": len(vessels), "aircraft": len(aircraft), "aircraft_type": len(types)}
