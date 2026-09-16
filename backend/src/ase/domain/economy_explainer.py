"""Bounded plain-English economic explainer text, written from supplied figures only.

The explainer never replaces the figures. It is a short, checked description of what the
dashboard already shows, so every bound here is a hard limit on what may be stored.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

REGION_IDS = ("WORLD", "GB", "US", "RU", "CN", "IR")
REGION_NAMES = {
    "WORLD": "Worldwide",
    "GB": "United Kingdom",
    "US": "United States",
    "RU": "Russia",
    "CN": "China",
    "IR": "Iran",
}
MAX_TAKEAWAY = 200
MAX_PARAGRAPH = 700
MAX_POINT = 180
MAX_TERM = 60
MAX_PLAIN_ENGLISH = 240
WORLD_PARAGRAPHS = (2, 3)
REGION_PARAGRAPHS = (1, 3)
WORLD_POINTS = (2, 4)
REGION_POINTS = (1, 4)
GLOSSARY_ENTRIES = (3, 12)
# At most one generation per fact-pack fingerprint, and never more often than this.
REGENERATION_INTERVAL = timedelta(hours=24)
# Only the current row and the one it replaced are kept.
RETAINED_ROWS = 2

ExplainerStatus = Literal[
    "ready", "stale", "generating", "empty", "unavailable", "validation_failed"
]


@dataclass(frozen=True, slots=True)
class ExplainerSection:
    takeaway: str
    paragraphs: tuple[str, ...]
    drivers: tuple[str, ...]
    watch: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GlossaryEntry:
    term: str
    plain_english: str


@dataclass(frozen=True, slots=True)
class ExplainerText:
    world: ExplainerSection
    regions: tuple[tuple[str, ExplainerSection], ...]
    glossary: tuple[GlossaryEntry, ...]

    def sections(self) -> tuple[tuple[str, ExplainerSection], ...]:
        return (("WORLD", self.world), *self.regions)


@dataclass(frozen=True, slots=True)
class StoredExplainer:
    fingerprint: str
    window_start: datetime
    text: ExplainerText
    model: str
    generated_at: datetime
    snapshot_fetched_at: datetime
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ExplainerView:
    """What a reader is told, including why nothing was written when that is the case."""

    status: ExplainerStatus
    stale: bool
    explainer: StoredExplainer | None = None
    reason: str | None = None
    sources: tuple[str, ...] = ()


def window_start(now: datetime) -> datetime:
    """Truncate to the hour so a stored window is stable and never carries seconds."""
    return now.replace(minute=0, second=0, microsecond=0)


def _section_payload(section: ExplainerSection) -> dict[str, Any]:
    return {
        "takeaway": section.takeaway,
        "paragraphs": list(section.paragraphs),
        "drivers": list(section.drivers),
        "watch": list(section.watch),
    }


def to_payload(text: ExplainerText) -> dict[str, Any]:
    return {
        "world": _section_payload(text.world),
        "regions": {key: _section_payload(section) for key, section in text.regions},
        "glossary": [
            {"term": entry.term, "plain_english": entry.plain_english} for entry in text.glossary
        ],
    }


def _strings(value: Any, limit: int) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError("Explainer list fields must be arrays of text.")
    if len(value) > 8:
        raise ValueError("Explainer list fields are bounded.")
    result = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item) > limit:
            raise ValueError("Explainer text exceeds its bounds.")
        result.append(item.strip())
    return tuple(result)


def _section(value: Any) -> ExplainerSection:
    if not isinstance(value, dict) or set(value) != {"takeaway", "paragraphs", "drivers", "watch"}:
        raise ValueError("Explainer sections need a takeaway, paragraphs, drivers and watch.")
    takeaway = value["takeaway"]
    if not isinstance(takeaway, str) or not takeaway.strip() or len(takeaway) > MAX_TAKEAWAY:
        raise ValueError("Explainer takeaway exceeds its bounds.")
    return ExplainerSection(
        takeaway.strip(),
        _strings(value["paragraphs"], MAX_PARAGRAPH),
        _strings(value["drivers"], MAX_POINT),
        _strings(value["watch"], MAX_POINT),
    )


def from_payload(payload: Mapping[str, Any]) -> ExplainerText:
    """Rebuild stored text, refusing anything outside the bounds that were checked."""
    if set(payload) != {"world", "regions", "glossary"}:
        raise ValueError("Stored explainer payload has unexpected fields.")
    regions = payload["regions"]
    if not isinstance(regions, dict) or not set(regions) <= set(REGION_IDS[1:]):
        raise ValueError("Stored explainer regions are not the known regions.")
    glossary = payload["glossary"]
    if not isinstance(glossary, list) or len(glossary) > GLOSSARY_ENTRIES[1]:
        raise ValueError("Stored explainer glossary is not a bounded list.")
    return ExplainerText(
        _section(payload["world"]),
        tuple((key, _section(regions[key])) for key in REGION_IDS[1:] if key in regions),
        tuple(_glossary_entry(entry) for entry in glossary),
    )


def _glossary_entry(entry: Any) -> GlossaryEntry:
    if not isinstance(entry, dict) or set(entry) != {"term", "plain_english"}:
        raise ValueError("Glossary entries need a term and a plain-English description.")
    term, plain = entry["term"], entry["plain_english"]
    if (
        not isinstance(term, str)
        or not isinstance(plain, str)
        or not term.strip()
        or not plain.strip()
        or len(term) > MAX_TERM
        or len(plain) > MAX_PLAIN_ENGLISH
    ):
        raise ValueError("Glossary entries exceed their bounds.")
    return GlossaryEntry(term.strip(), plain.strip())


def all_text(text: ExplainerText) -> tuple[str, ...]:
    """Every generated string, for the mechanical checks that run before storage."""
    result: list[str] = []
    for _key, section in text.sections():
        result.append(section.takeaway)
        result.extend(section.paragraphs)
        result.extend(section.drivers)
        result.extend(section.watch)
    for entry in text.glossary:
        result.extend((entry.term, entry.plain_english))
    return tuple(result)


def section_bounds(key: str) -> tuple[tuple[int, int], tuple[int, int]]:
    """Paragraph and list-item counts allowed for the world summary or one region."""
    return (
        (WORLD_PARAGRAPHS, WORLD_POINTS) if key == "WORLD" else (REGION_PARAGRAPHS, REGION_POINTS)
    )


def missing_regions(text: ExplainerText, expected: Sequence[str]) -> tuple[str, ...]:
    written = {key for key, _section in text.regions}
    return tuple(key for key in expected if key != "WORLD" and key not in written)
