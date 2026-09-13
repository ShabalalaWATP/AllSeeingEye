"""Packaged reference notes, validated once at load; never a user-supplied path."""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from importlib.resources import files
from typing import Any

from ase.domain.reference import (
    KINDS,
    MAX_ENTRIES,
    ReferenceCatalogue,
    ReferenceEntry,
    ReferenceKind,
    ReferenceLink,
    normalise_key,
)


def _text(value: Any, limit: int) -> str:
    return " ".join(str(value).split())[:limit] if isinstance(value, str) else ""


def _links(raw: Any) -> tuple[ReferenceLink, ...]:
    links: list[ReferenceLink] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        url, label = _text(item.get("url"), 400), _text(item.get("label"), 60)
        if url.startswith("https://") and label:
            links.append(ReferenceLink(label, url))
    return tuple(links[:4])


def parse_entry(kind: ReferenceKind, raw: dict[str, Any], provenance: str) -> ReferenceEntry | None:
    key = normalise_key(kind, _text(raw.get("key"), 40))
    name = _text(raw.get("name"), 120)
    if not key or not name:
        return None
    return ReferenceEntry(
        kind=kind,
        key=key,
        name=name,
        description=_text(raw.get("description"), 300),
        detail=_text(raw.get("detail"), 200),
        links=_links(raw.get("links")),
        provenance=_text(raw.get("provenance"), 200) or provenance,
    )


def parse_catalogue(raw: dict[str, Any]) -> ReferenceCatalogue:
    retrieved = _text(raw.get("retrieved_at"), 40)
    provenance = _text(raw.get("source"), 200) or "Packaged reference notes"
    entries: dict[ReferenceKind, dict[str, ReferenceEntry]] = {}
    for kind in KINDS:
        items = raw.get(kind, [])
        if not isinstance(items, list) or len(items) > MAX_ENTRIES[kind]:
            raise ValueError(f"Reference {kind} entries outside the bound")
        table: dict[str, ReferenceEntry] = {}
        for item in items:
            entry = parse_entry(kind, item, provenance) if isinstance(item, dict) else None
            if entry is not None and entry.key not in table:
                table[entry.key] = entry
        entries[kind] = table
    return ReferenceCatalogue(retrieved_at=datetime.fromisoformat(retrieved), entries=entries)


@lru_cache(maxsize=1)
def load_reference() -> ReferenceCatalogue:
    text = files("ase.resources").joinpath("reference_entities.json").read_text(encoding="utf-8")
    return parse_catalogue(json.loads(text))
