"""Reference notes for things the map shows by identifier: ships, aircraft, aircraft types.

A note is public background (name, description, links) keyed by the identifier a feed
broadcasts. It never confirms that the observed object is the noted one: identifiers
are reused, spoofed and mistyped, so the UI states the key that matched.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

ReferenceKind = Literal["vessel", "aircraft", "aircraft_type"]
KINDS: tuple[ReferenceKind, ...] = ("vessel", "aircraft", "aircraft_type")
MAX_LOOKUP_KEYS = 50
MAX_KEY_LENGTH = 32
MAX_ENTRIES = {"vessel": 4_000, "aircraft": 1_000, "aircraft_type": 300}


@dataclass(frozen=True, slots=True)
class ReferenceLink:
    label: str
    url: str


@dataclass(frozen=True, slots=True)
class ReferenceEntry:
    kind: ReferenceKind
    key: str
    name: str
    description: str
    detail: str
    links: tuple[ReferenceLink, ...]
    provenance: str


@dataclass(frozen=True, slots=True)
class ReferenceCatalogue:
    retrieved_at: datetime
    entries: dict[ReferenceKind, dict[str, ReferenceEntry]]

    def lookup(self, kind: ReferenceKind, keys: tuple[str, ...]) -> tuple[ReferenceEntry, ...]:
        table = self.entries.get(kind, {})
        found: list[ReferenceEntry] = []
        seen: set[str] = set()
        for raw in keys[:MAX_LOOKUP_KEYS]:
            key = normalise_key(kind, raw)
            if key and key not in seen and key in table:
                seen.add(key)
                found.append(table[key])
        return tuple(found)


def normalise_key(kind: ReferenceKind, raw: str) -> str:
    """MMSIs are nine digits; registrations and type codes are upper-case without separators."""
    text = raw.strip()[:MAX_KEY_LENGTH]
    if kind == "vessel":
        digits = re.sub(r"\D", "", text)
        return digits if len(digits) == 9 else ""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", text).upper()
    return cleaned if 2 <= len(cleaned) <= 12 else ""
