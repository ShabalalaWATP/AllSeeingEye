"""Provider frontlines and spotted losses: reported geometry with its provider stamp, never fact."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from ase.domain.ukraine.control import Polygon

MAX_FRONTLINE_VERTICES = 60_000
MAX_FRONTLINE_FEATURES = 400
MAX_SPOTTED = 3_000

Line = tuple[tuple[float, float], ...]


class FrontlineKind(StrEnum):
    OCCUPIED = "occupied"
    LIBERATED = "liberated"
    UNKNOWN = "unknown"
    HISTORICAL = "historical"
    LINE = "line"


class FrontlineStatus(StrEnum):
    DISABLED = "disabled"
    READY = "ready"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class FrontlineFeature:
    kind: FrontlineKind
    label: str
    polygons: tuple[Polygon, ...] = ()
    lines: tuple[Line, ...] = ()

    @property
    def vertices(self) -> int:
        return sum(len(r) for p in self.polygons for r in p) + sum(len(line) for line in self.lines)


@dataclass(frozen=True, slots=True)
class FrontlineSnapshot:
    provider: str
    attribution: str
    terms: str
    assessed_at: str | None
    downloaded_at: datetime
    features: tuple[FrontlineFeature, ...]

    def __post_init__(self) -> None:
        if len(self.features) > MAX_FRONTLINE_FEATURES:
            raise ValueError("Frontline snapshot exceeds the feature bound")
        if sum(feature.vertices for feature in self.features) > MAX_FRONTLINE_VERTICES:
            raise ValueError("Frontline snapshot exceeds the vertex bound")


@dataclass(frozen=True, slots=True)
class FrontlineState:
    status: FrontlineStatus
    reason: str
    snapshot: FrontlineSnapshot | None = None


@dataclass(frozen=True, slots=True)
class SpottedLoss:
    id: int
    lat: float
    lon: float
    model: str
    equipment_type: str
    status: str
    lost_by: str
    on: date
    place: str


@dataclass(frozen=True, slots=True)
class SpottedState:
    status: FrontlineStatus
    reason: str
    attribution: str
    downloaded_at: datetime | None
    losses: tuple[SpottedLoss, ...] = ()

    def __post_init__(self) -> None:
        if len(self.losses) > MAX_SPOTTED:
            raise ValueError("Spotted losses exceed the bound")
