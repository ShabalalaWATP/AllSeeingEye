"""The fusion core: every feed item becomes one Event."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import IntEnum, StrEnum
from types import MappingProxyType

JsonScalar = str | int | float | bool | None

MAX_TITLE = 300
MAX_SUMMARY = 2_000
MAX_ATTRIBUTES = 40


class Category(StrEnum):
    NEWS = "news"
    CONFLICT = "conflict"
    DISASTER = "disaster"
    AVIATION = "aviation"
    MARITIME = "maritime"
    SPACE = "space"
    CYBER = "cyber"
    SOCIAL = "social"
    POLITICAL = "political"
    HUMANITARIAN = "humanitarian"
    ECONOMIC = "economic"


class GeoConfidence(StrEnum):
    EXACT = "exact"
    CITY = "city"
    ADMIN1 = "admin1"
    COUNTRY = "country"
    NONE = "none"


class Reliability(StrEnum):
    """NATO source reliability (AJP-2.1 Table 3.1)."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


class Credibility(IntEnum):
    """NATO information credibility (AJP-2.1 Table 3.1)."""

    CONFIRMED = 1
    PROBABLY_TRUE = 2
    POSSIBLY_TRUE = 3
    DOUBTFUL = 4
    IMPROBABLE = 5
    CANNOT_BE_JUDGED = 6


@dataclass(frozen=True, slots=True)
class Point:
    lon: float
    lat: float

    def __post_init__(self) -> None:
        if not -180.0 <= self.lon <= 180.0 or not -90.0 <= self.lat <= 90.0:
            msg = f"Coordinates out of range: lon={self.lon} lat={self.lat}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class BoundingBox:
    west: float
    south: float
    east: float
    north: float

    def contains(self, point: Point) -> bool:
        if not self.south <= point.lat <= self.north:
            return False
        if self.west <= self.east:
            return self.west <= point.lon <= self.east
        # Crosses the antimeridian.
        return point.lon >= self.west or point.lon <= self.east


def event_id(source_id: str, upstream_key: str) -> str:
    """Stable identifier: the same upstream item always maps to the same id."""
    return hashlib.sha256(f"{source_id}\x1f{upstream_key}".encode()).hexdigest()[:32]


def content_hash(*parts: str | None) -> str:
    joined = "\x1f".join(part or "" for part in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Event:
    id: str
    source_id: str
    category: Category
    subtype: str
    title: str
    published_at: datetime
    observed_at: datetime
    reliability: Reliability
    summary: str | None = None
    url: str | None = None
    language: str = "en"
    title_en: str | None = None
    point: Point | None = None
    geo_confidence: GeoConfidence = GeoConfidence.NONE
    country_iso: str | None = None
    tags: frozenset[str] = field(default_factory=frozenset)
    severity: float | None = None
    credibility: Credibility = Credibility.CANNOT_BE_JUDGED
    grade_rationale: str = ""
    story_id: str | None = None
    attributes: Mapping[str, JsonScalar] = field(default_factory=lambda: MappingProxyType({}))
    content_hash: str = ""

    @property
    def grade(self) -> str:
        return f"{self.reliability.value}{self.credibility.value}"

    def with_changes(self, **changes: object) -> Event:
        """Return a copy with the given fields replaced."""
        return replace(self, **changes)  # type: ignore[arg-type]


def freeze_attributes(attributes: Mapping[str, JsonScalar]) -> Mapping[str, JsonScalar]:
    """Bound and freeze category-specific extras."""
    items = list(attributes.items())[:MAX_ATTRIBUTES]
    return MappingProxyType(dict(items))
