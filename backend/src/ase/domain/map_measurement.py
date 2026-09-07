"""Reproducible operator-entered coordinates, never client-asserted measurement results."""

from dataclasses import dataclass
from typing import Any

METHOD = "wgs84-geographiclib-2.2.0-v1"
MAX_POINTS = 32


@dataclass(frozen=True, slots=True)
class MapMeasurement:
    mode: str
    points: tuple[tuple[float, float], ...]
    method: str = METHOD

    def __post_init__(self) -> None:
        if self.mode not in ("distance", "area") or self.method != METHOD:
            raise ValueError("Unsupported map measurement method or mode")
        if type(self.points) is not tuple or len(self.points) > MAX_POINTS:
            raise ValueError("Map measurement allows at most 32 points")
        for point in self.points:
            if type(point) is not tuple or len(point) != 2:
                raise ValueError("Map measurement requires longitude/latitude pairs")
            for value, limit in zip(point, (180, 90), strict=True):
                if type(value) not in (int, float) or not -limit <= value <= limit:
                    raise ValueError("Invalid map measurement coordinate")


def measurement_from_dict(value: Any) -> MapMeasurement | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"mode", "points", "method"}:
        raise ValueError("Invalid map measurement fields")
    points = value["points"]
    if not isinstance(points, list) or len(points) > MAX_POINTS:
        raise ValueError("Invalid map measurement points")
    if any(not isinstance(point, list) or len(point) != 2 for point in points):
        raise ValueError("Invalid map measurement coordinate pairs")
    return MapMeasurement(value["mode"], tuple(tuple(point) for point in points), value["method"])


def measurement_to_dict(value: MapMeasurement) -> dict[str, Any]:
    return {
        "mode": value.mode,
        "method": value.method,
        "points": [list(point) for point in value.points],
    }
