"""Ephemeral routing estimates, separate from verified research evidence."""

from dataclasses import dataclass
from typing import Literal

from ase.domain.events import Point

RouteMode = Literal["driving", "walking", "cycling"]


@dataclass(frozen=True, slots=True)
class RouteStep:
    instruction: str
    distance_km: float
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class NavigationRoute:
    mode: RouteMode
    distance_km: float
    duration_seconds: float
    coordinates: tuple[Point, ...]
    steps: tuple[RouteStep, ...]
