"""Operator-run import of a bounded office-holder roster from Wikidata and Wikimedia Commons.

Runs only from the CLI, never at request time. Names, offices and portraits are the
public record as Wikidata describes it on the retrieval date; the roster carries that
date so stale incumbents are visible. Portrait licences are recorded per image.
"""

from __future__ import annotations

import base64
import html
import io
import json
import re
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, unquote

import httpx
from PIL import Image, ImageDraw

from ase.adapters.geo.public_figures_targets import COUNTRIES, ORGANISATIONS

SPARQL = "https://query.wikidata.org/sparql"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia's robot policy requires a contact in the User-Agent; the CLI can override it.
DEFAULT_CONTACT = "https://github.com/ShabalalaWATP/OSINT"
PORTRAIT_SIZE = 64
MAX_PORTRAIT_BYTES = 300_000
QUERY_PAUSE_SECONDS = 2.0
LABEL_SERVICE = 'SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". }'
ROLE_WORDS = {
    "head_of_government": ("prime minister", "premier", "chancellor", "head of government"),
    "head_of_state": ("president", "monarch", "king", "queen", "emperor", "supreme leader"),
}


def _lang_en(var: str) -> str:
    return f'FILTER(LANG(?{var}) = "en")'


def _sparql(client: httpx.Client, query: str) -> list[dict[str, Any]]:
    """One query with a polite pause; a 429 is retried once after the advertised wait."""
    time.sleep(QUERY_PAUSE_SECONDS)
    headers = {"Accept": "application/sparql-results+json"}
    response = client.get(SPARQL, params={"query": query}, headers=headers)
    if response.status_code == 429:
        time.sleep(min(float(response.headers.get("Retry-After", "30")), 120.0))
        response = client.get(SPARQL, params={"query": query}, headers=headers)
    response.raise_for_status()
    rows = response.json()["results"]["bindings"]
    if not isinstance(rows, list) or len(rows) > 5_000:
        raise ValueError("Unexpected SPARQL result shape")
    return [{key: value.get("value") for key, value in row.items()} for row in rows]


def _qid(uri: str | None) -> str | None:
    return uri.rsplit("/", 1)[-1] if uri else None


def _point(value: str | None) -> tuple[float, float] | None:
    match = re.fullmatch(r"Point\(([-0-9.]+) ([-0-9.]+)\)", value or "")
    return (float(match.group(2)), float(match.group(1))) if match else None


def _values(qids: list[str]) -> str:
    return " ".join(f"wd:{qid}" for qid in qids)


def country_rows(client: httpx.Client) -> list[dict[str, Any]]:
    return _sparql(
        client,
        "SELECT ?country ?hos ?hog ?hosOffice ?hogOffice ?capLabel ?coord WHERE { "
        f"VALUES ?country {{ {_values([qid for _, qid in COUNTRIES])} }} "
        "OPTIONAL { ?country wdt:P35 ?hos } OPTIONAL { ?country wdt:P6 ?hog } "
        "OPTIONAL { ?country wdt:P1906 ?hosOffice } OPTIONAL { ?country wdt:P1313 ?hogOffice } "
        "OPTIONAL { ?country wdt:P36 ?cap . ?cap wdt:P625 ?coord } " + LABEL_SERVICE + " }",
    )


def position_holder(client: httpx.Client, office: str) -> str | None:
    rows = _sparql(
        client,
        "SELECT ?person ?start WHERE { "
        f'?pos rdfs:label "{office}"@en . ?person p:P39 ?s . ?s ps:P39 ?pos . '
        "FILTER NOT EXISTS { ?s pq:P582 ?end } OPTIONAL { ?s pq:P580 ?start } } "
        "ORDER BY DESC(?start) LIMIT 1",
    )
    return _qid(rows[0]["person"]) if rows else None


def person_details(client: httpx.Client, qids: list[str]) -> dict[str, dict[str, Any]]:
    """Label (English, else the multilingual default), portrait file and English aliases."""
    rows = _sparql(
        client,
        f"SELECT ?person ?personLabel ?image ?alias WHERE {{ VALUES ?person {{ {_values(qids)} }} "
        "OPTIONAL { ?person wdt:P18 ?image } "
        "OPTIONAL { ?person skos:altLabel ?alias "
        + _lang_en("alias")
        + " } "
        + LABEL_SERVICE
        + " }",
    )
    details: dict[str, dict[str, Any]] = {}
    for row in rows:
        qid = _qid(row["person"]) or ""
        detail = details.setdefault(
            qid,
            {"name": row.get("personLabel") or qid, "image": row.get("image"), "aliases": set()},
        )
        alias = (row.get("alias") or "").strip()
        if 3 <= len(alias) <= 60:
            detail["aliases"].add(alias)
    for detail in details.values():
        detail["aliases"] = sorted(detail["aliases"])[:12]
    return details


def current_positions(client: httpx.Client, qids: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Open-ended positions held, with jurisdiction, so titles come from the person's record."""
    rows = _sparql(
        client,
        "SELECT ?person ?pos ?posLabel ?juris ?start WHERE { "
        f"VALUES ?person {{ {_values(qids)} }} "
        "?person p:P39 ?s . ?s ps:P39 ?pos . FILTER NOT EXISTS { ?s pq:P582 ?end } "
        "OPTIONAL { ?s pq:P580 ?start } OPTIONAL { ?pos wdt:P1001 ?juris } " + LABEL_SERVICE + " }",
    )
    positions: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        positions.setdefault(_qid(row["person"]) or "", []).append(
            {
                "office": _qid(row.get("pos")),
                "label": row.get("posLabel") or "",
                "jurisdiction": _qid(row.get("juris")),
                "start": row.get("start") or "",
            }
        )
    return positions


def office_title(
    positions: list[dict[str, Any]], declared_office: str | None, country_qid: str, role: str
) -> str:
    """Prefer the country's declared office item, then a role-like current post, newest first."""
    for position in positions:
        if declared_office and position["office"] == declared_office:
            return _title(position["label"])
    words = ROLE_WORDS["head_of_government" if role == "head_of_government" else "head_of_state"]
    ranked = sorted(
        positions,
        key=lambda p: (
            any(word in p["label"].casefold() for word in words),
            p["jurisdiction"] == country_qid,
            p["start"],
        ),
        reverse=True,
    )
    if ranked and any(word in ranked[0]["label"].casefold() for word in words):
        return _title(ranked[0]["label"])
    return "Head of government" if role == "head_of_government" else "Head of state"


def _title(label: str) -> str:
    return label[:1].upper() + label[1:] if label else label


def _plain(value: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]*>", "", value)).split())[:300]


def portrait(client: httpx.Client, image_url: str) -> dict[str, str] | None:
    """Fetch, square-crop and mask one Commons portrait; keep its licence and credit."""
    filename = unquote(image_url.rsplit("/", 1)[-1])
    info = client.get(
        COMMONS_API,
        params={
            "action": "query",
            "titles": f"File:{filename}",
            "prop": "imageinfo",
            "iiprop": "extmetadata",
            "format": "json",
        },
    )
    info.raise_for_status()
    pages: dict[str, Any] = info.json().get("query", {}).get("pages", {})
    page: dict[str, Any] = next(iter(pages.values()), {})
    meta: dict[str, Any] = (page.get("imageinfo") or [{}])[0].get("extmetadata", {})
    licence = _plain(meta.get("LicenseShortName", {}).get("value", "")) or "Unknown"
    credit = _plain(meta.get("Artist", {}).get("value", "")) or "Wikimedia Commons"
    image = client.get(
        f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(filename)}",
        params={"width": 160},
        follow_redirects=True,
    )
    image.raise_for_status()
    if len(image.content) > MAX_PORTRAIT_BYTES:
        return None
    return {
        "png_base64": base64.b64encode(circular_png(image.content)).decode("ascii"),
        "licence": licence,
        "credit": credit,
        "source_url": f"https://commons.wikimedia.org/wiki/File:{quote(filename)}",
    }


def circular_png(raw: bytes) -> bytes:
    picture = Image.open(io.BytesIO(raw)).convert("RGB")
    side = min(picture.size)
    left, top = (picture.width - side) // 2, max(0, (picture.height - side) // 4)
    square = picture.crop((left, top, left + side, top + side)).resize(
        (PORTRAIT_SIZE, PORTRAIT_SIZE), Image.Resampling.LANCZOS
    )
    mask = Image.new("L", (PORTRAIT_SIZE, PORTRAIT_SIZE), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, PORTRAIT_SIZE - 1, PORTRAIT_SIZE - 1), fill=255)
    circular = Image.new("RGBA", (PORTRAIT_SIZE, PORTRAIT_SIZE), (0, 0, 0, 0))
    circular.paste(square, (0, 0), mask)
    buffer = io.BytesIO()
    circular.quantize(colors=96, method=Image.Quantize.FASTOCTREE).save(
        buffer, format="PNG", optimize=True
    )
    return buffer.getvalue()


def _country_entries(row: dict[str, Any], seat: tuple[float, float]) -> list[dict[str, Any]]:
    iso = next(iso for iso, qid in COUNTRIES if qid == _qid(row["country"]))
    hos, hog = _qid(row.get("hos")), _qid(row.get("hog"))
    base = {
        "country_iso": iso,
        "country_qid": _qid(row["country"]),
        "organisation": None,
        "seat": {
            "name": row.get("capLabel") or "Seat of government",
            "lat": seat[0],
            "lon": seat[1],
        },
    }
    state = {**base, "id": f"{iso.lower()}-head-of-state", "person": hos}
    state["declared_office"] = _qid(row.get("hosOffice"))
    if hos and hos == hog:
        return [{**state, "role": "head_of_state_and_government"}]
    entries = [{**state, "role": "head_of_state"}] if hos else []
    if hog:
        entries.append(
            {
                **base,
                "id": f"{iso.lower()}-head-of-government",
                "person": hog,
                "role": "head_of_government",
                "declared_office": _qid(row.get("hogOffice")),
            }
        )
    return entries


def build_roster(client: httpx.Client, now: datetime) -> dict[str, Any]:
    entries: dict[str, dict[str, Any]] = {}
    for row in country_rows(client):
        seat = _point(row.get("coord"))
        if seat is None:
            continue
        for entry in _country_entries(row, seat):
            entries.setdefault(entry["id"], entry)  # first capital row wins
    for key, organisation, office, seat_name, lat, lon in ORGANISATIONS:
        holder = position_holder(client, office)
        if holder:
            entries[key] = {
                "id": key,
                "person": holder,
                "office": office,
                "role": "organisation",
                "country_iso": None,
                "organisation": organisation,
                "seat": {"name": seat_name, "lat": lat, "lon": lon},
            }
    people = sorted({entry["person"] for entry in entries.values()})
    details = person_details(client, people)
    positions = current_positions(client, people)
    portraits = {
        qid: portrait(client, details[qid]["image"])
        for qid in people
        if details.get(qid, {}).get("image")
    }
    figures = []
    for entry in sorted(entries.values(), key=lambda item: item["id"]):
        qid = entry["person"]
        detail = details.get(qid, {"name": qid, "aliases": []})
        office = entry.get("office") or office_title(
            positions.get(qid, []),
            entry.get("declared_office"),
            entry.get("country_qid") or "",
            entry["role"],
        )
        figures.append(
            {
                "id": entry["id"],
                "wikidata_id": qid,
                "name": detail["name"],
                "office": office,
                "role": entry["role"],
                "country_iso": entry["country_iso"],
                "organisation": entry["organisation"],
                "aliases": detail["aliases"],
                "seat": entry["seat"],
                "portrait": portraits.get(qid),
            }
        )
    return {
        "schema_version": 1,
        "source": "Wikidata (CC0) via the public SPARQL endpoint; portraits from Wikimedia "
        "Commons under the licence recorded per image",
        "retrieved_at": now.astimezone(UTC).isoformat(),
        "figures": figures,
    }


def import_public_figures(
    destination: str, now: datetime | None = None, contact: str = DEFAULT_CONTACT
) -> int:
    agent = f"TheAllSeeingEye/0.1 ({contact}; operator-run roster import) httpx"
    with httpx.Client(timeout=60, headers={"User-Agent": agent}) as client:
        roster = build_roster(client, now or datetime.now(UTC))
    with open(destination, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(roster, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    return len(roster["figures"])
