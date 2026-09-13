"""Reported territorial control: a majority vote of public maps, never observed positions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

MAX_SETTLEMENTS = 12_000
MAX_AREA_VERTICES = 60_000
MAX_OUTLINE_VERTICES = 20_000
MAX_OUTLINES = 30
MAX_CHANGES = 300
MAX_OBLASTS = 30
MAX_NAME = 80

Ring = tuple[tuple[float, float], ...]
Polygon = tuple[Ring, ...]


class ControlStatus(StrEnum):
    UA = "ua"
    RU = "ru"
    CONTESTED = "contested"
    UNKNOWN = "unknown"


_STATUS_WORDS = {
    "UA": ControlStatus.UA,
    "RU": ControlStatus.RU,
    "CONTESTED": ControlStatus.CONTESTED,
}


def parse_status(value: str) -> ControlStatus:
    """The source writes UA, RU or CONTESTED; anything else is an absent vote."""
    return _STATUS_WORDS.get(value.strip().upper(), ControlStatus.UNKNOWN)


@dataclass(frozen=True, slots=True)
class SettlementControl:
    geoname_id: int
    name: str
    oblast: str
    lat: float
    lon: float
    status: ControlStatus
    since: date | None
    # Wikipedia, Wikipedia boosted by news reports, DeepState, ISW, in that order.
    votes: tuple[ControlStatus, ControlStatus, ControlStatus, ControlStatus]


@dataclass(frozen=True, slots=True)
class ControlChange:
    geoname_id: int
    name: str
    oblast: str
    previous: ControlStatus
    status: ControlStatus
    changed_on: date


@dataclass(frozen=True, slots=True)
class OblastControl:
    name: str
    total: int
    ua: int
    ru: int
    contested: int
    unknown: int


def _vertices(polygons: tuple[Polygon, ...]) -> int:
    return sum(len(ring) for polygon in polygons for ring in polygon)


@dataclass(frozen=True, slots=True)
class ControlArea:
    """Settlement cells of one status dissolved into a display area, simplified."""

    status: ControlStatus
    polygons: tuple[Polygon, ...]

    @property
    def vertices(self) -> int:
        return _vertices(self.polygons)


@dataclass(frozen=True, slots=True)
class NamedOutline:
    name: str
    iso: str
    polygons: tuple[Polygon, ...]

    @property
    def vertices(self) -> int:
        return _vertices(self.polygons)


@dataclass(frozen=True, slots=True)
class ControlSnapshot:
    assessment_date: date
    release_stamp: str
    retrieved_at: datetime
    attribution: str
    licence: str
    source_url: str
    method_note: str
    places_total: int
    settlements: tuple[SettlementControl, ...]
    areas: tuple[ControlArea, ...]
    oblasts: tuple[OblastControl, ...]
    changes: tuple[ControlChange, ...]

    def __post_init__(self) -> None:
        if not 0 < len(self.settlements) <= MAX_SETTLEMENTS:
            raise ValueError("Control snapshot settlement count outside the bound")
        if sum(area.vertices for area in self.areas) > MAX_AREA_VERTICES:
            raise ValueError("Control snapshot areas exceed the vertex bound")
        if len(self.oblasts) > MAX_OBLASTS or len(self.changes) > MAX_CHANGES:
            raise ValueError("Control snapshot oblast or change count outside the bound")
        if self.places_total < len(self.settlements):
            raise ValueError("Control snapshot cannot retain more places than it counted")

    def count(self, status: ControlStatus) -> int:
        return sum(getattr(oblast, status.value) for oblast in self.oblasts)
