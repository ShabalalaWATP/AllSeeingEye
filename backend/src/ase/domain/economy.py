"""Source-labelled economic observations, never prices invented from missing data."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

SeriesStatus = Literal["available", "stale", "unavailable"]
SeriesFrequency = Literal["annual", "daily"]


@dataclass(frozen=True, slots=True)
class EconomyPoint:
    date: str
    value: float | None


@dataclass(frozen=True, slots=True)
class EconomySeries:
    id: str
    name: str
    unit: str
    frequency: SeriesFrequency
    provider: str
    source_url: str
    status: SeriesStatus
    note: str
    updated_at: datetime | None
    points: tuple[EconomyPoint, ...] = ()
    source_updated_at: str | None = None


@dataclass(frozen=True, slots=True)
class EconomyRegion:
    id: str
    name: str
    series: tuple[EconomySeries, ...]


@dataclass(frozen=True, slots=True)
class EconomySnapshot:
    fetched_at: datetime
    refresh_after: datetime
    regions: tuple[EconomyRegion, ...]
    fx: tuple[EconomySeries, ...]
