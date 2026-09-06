"""Ephemeral satellite-catalogue footprints, separate from observed event geometry."""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

Position = tuple[float, float]
Ring = tuple[Position, ...]
Polygon = tuple[Ring, ...]


@dataclass(frozen=True, slots=True)
class FootprintQuery:
    bbox: tuple[float, float, float, float]
    since: datetime
    until: datetime
    disclose_to_provider: bool

    def __post_init__(self) -> None:
        west, south, east, north = self.bbox
        if not self.disclose_to_provider:
            raise ValueError("Confirm disclosure of the selected area and dates to Copernicus.")
        if not all(math.isfinite(value) for value in self.bbox) or not (
            -180 <= west < east <= 180
            and -90 <= south < north <= 90
            and east - west <= 10
            and north - south <= 10
        ):
            raise ValueError(
                "Use a WGS84 box no wider or taller than 10 degrees, without wrapping."
            )
        if self.since.utcoffset() is None or self.until.utcoffset() is None:
            raise ValueError("Catalogue dates must include a timezone.")
        if not timedelta(0) < self.until - self.since <= timedelta(days=14):
            raise ValueError("Select a positive catalogue interval of at most 14 days.")


@dataclass(frozen=True, slots=True)
class Footprint:
    id: str
    polygons: tuple[Polygon, ...]
    collection: str
    captured_at: datetime
    cloud_cover: float | None
    source_url: str
    licence: str
    licence_url: str


@dataclass(frozen=True, slots=True)
class FootprintCollection:
    features: tuple[Footprint, ...]
    status: Literal["completed", "empty", "unavailable"]
    truncated: bool
    limitations: str
    queried_at: datetime
