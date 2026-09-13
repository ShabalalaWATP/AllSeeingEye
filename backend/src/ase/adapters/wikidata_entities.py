"""Bounded Wikidata entity lookups (search and fetch) for operator-run imports.

Uses the MediaWiki action API rather than SPARQL, which is often overloaded. Every call
carries a contact User-Agent, runs only from CLI importers, and returns plain values.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

API = "https://www.wikidata.org/w/api.php"
DEFAULT_CONTACT = "https://github.com/ShabalalaWATP/OSINT"
PAUSE_SECONDS = 0.6
BATCH = 50


@dataclass(frozen=True, slots=True)
class EntityFacts:
    qid: str
    label: str
    description: str
    coords: tuple[float, float] | None  # (lon, lat)
    operators: tuple[str, ...]
    owners: tuple[str, ...]
    country: str | None
    website: str | None
    wikipedia: str | None
    inception: str | None = None
    parent: tuple[str, ...] = field(default_factory=tuple)


class WikidataEntities:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client
        self._labels: dict[str, str] = {}

    @classmethod
    def open(cls, contact: str = DEFAULT_CONTACT) -> WikidataEntities:
        agent = f"TheAllSeeingEye/0.1 ({contact}; operator-run reference import) httpx"
        return cls(httpx.Client(timeout=60, headers={"User-Agent": agent}))

    def close(self) -> None:
        self._client.close()

    def _get(self, params: dict[str, str]) -> dict[str, Any]:
        time.sleep(PAUSE_SECONDS)
        try:
            response = self._client.get(API, params={**params, "format": "json"})
        except httpx.TransportError:
            time.sleep(15.0)  # the endpoint drops connections under load; one retry
            response = self._client.get(API, params={**params, "format": "json"})
        if response.status_code == 429:
            time.sleep(min(float(response.headers.get("Retry-After", "20")), 120.0))
            response = self._client.get(API, params={**params, "format": "json"})
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Unexpected Wikidata response")
        return data

    def search(self, text: str, limit: int = 5) -> list[tuple[str, str, str]]:
        data = self._get(
            {
                "action": "wbsearchentities",
                "search": text[:200],
                "language": "en",
                "type": "item",
                "limit": str(min(limit, 10)),
            }
        )
        return [
            (str(hit.get("id")), str(hit.get("label", "")), str(hit.get("description", "")))
            for hit in data.get("search", [])
            if re.fullmatch(r"Q\d+", str(hit.get("id")))
        ]

    def labels(self, qids: list[str]) -> dict[str, str]:
        missing = [qid for qid in dict.fromkeys(qids) if qid not in self._labels]
        for start in range(0, len(missing), BATCH):
            chunk = missing[start : start + BATCH]
            data = self._get(
                {
                    "action": "wbgetentities",
                    "ids": "|".join(chunk),
                    "props": "labels",
                    "languages": "en",
                }
            )
            for qid, entity in data.get("entities", {}).items():
                self._labels[qid] = str(entity.get("labels", {}).get("en", {}).get("value", qid))
        return {qid: self._labels.get(qid, qid) for qid in qids}

    def facts(self, qids: list[str]) -> dict[str, EntityFacts]:
        found: dict[str, EntityFacts] = {}
        wanted = [qid for qid in dict.fromkeys(qids) if re.fullmatch(r"Q\d+", qid)]
        for start in range(0, len(wanted), BATCH):
            chunk = wanted[start : start + BATCH]
            data = self._get(
                {
                    "action": "wbgetentities",
                    "ids": "|".join(chunk),
                    "props": "labels|descriptions|claims|sitelinks/urls",
                    "languages": "en",
                    "sitefilter": "enwiki",
                }
            )
            for qid, entity in data.get("entities", {}).items():
                if "missing" in entity:
                    continue
                found[qid] = _facts(qid, entity)
        related = [q for f in found.values() for q in (*f.operators, *f.owners, *f.parent)]
        related += [f.country for f in found.values() if f.country]
        names = {q: label for q, label in self.labels(related).items() if label != q}
        return {
            qid: EntityFacts(
                qid=f.qid,
                label=f.label,
                description=f.description,
                coords=f.coords,
                operators=tuple(names[q] for q in f.operators if q in names),
                owners=tuple(names[q] for q in f.owners if q in names),
                country=names.get(f.country) if f.country else None,
                website=f.website,
                wikipedia=f.wikipedia,
                inception=f.inception,
                parent=tuple(names[q] for q in f.parent if q in names),
            )
            for qid, f in found.items()
        }


def _claim_ids(claims: dict[str, Any], prop: str) -> tuple[str, ...]:
    ids: list[str] = []
    for statement in claims.get(prop, [])[:4]:
        value = statement.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and re.fullmatch(r"Q\d+", str(value.get("id", ""))):
            ids.append(str(value["id"]))
    return tuple(ids)


def _claim_text(claims: dict[str, Any], prop: str) -> str | None:
    for statement in claims.get(prop, [])[:1]:
        value = statement.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, str):
            return str(value)[:300]
        if isinstance(value, dict) and isinstance(value.get("time"), str):
            return str(value["time"])[1:11]
    return None


def _facts(qid: str, entity: dict[str, Any]) -> EntityFacts:
    claims = entity.get("claims", {})
    coords: tuple[float, float] | None = None
    for statement in claims.get("P625", [])[:1]:
        value = statement.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        lon, lat = value.get("longitude"), value.get("latitude")
        if isinstance(lon, int | float) and isinstance(lat, int | float):
            coords = (float(lon), float(lat))
    website = _claim_text(claims, "P856")
    countries = _claim_ids(claims, "P17")
    return EntityFacts(
        qid=qid,
        label=str(entity.get("labels", {}).get("en", {}).get("value", "")),
        description=str(entity.get("descriptions", {}).get("en", {}).get("value", "")),
        coords=coords,
        operators=_claim_ids(claims, "P137"),
        owners=_claim_ids(claims, "P127"),
        country=countries[0] if countries else None,
        website=website if website and website.startswith("https://") else None,
        wikipedia=str(entity.get("sitelinks", {}).get("enwiki", {}).get("url", "")) or None,
        inception=_claim_text(claims, "P571"),
        parent=_claim_ids(claims, "P749"),
    )
