"""Bounded nearest-pixel DEM sampling in the Terrarium Web Mercator grid."""

import math

from ase.domain.events import Point

TERRAIN_ZOOM = 10
TILE_SIZE = 256
MERCATOR_LIMIT = 85.05112878
MAX_TERRAIN_POSITIONS = 1000
MAX_TERRAIN_TILES = 64
TileCoordinate = tuple[int, int]


def terrain_pixel(point: Point) -> tuple[TileCoordinate, int, int]:
    if not math.isfinite(point.lat) or abs(point.lat) > MERCATOR_LIMIT:
        raise ValueError("Terrain sampling excludes the polar Web Mercator limits.")
    scale = TILE_SIZE * 2**TERRAIN_ZOOM
    x = int(((point.lon + 180) / 360 % 1) * scale)
    mercator_y = (1 - math.asinh(math.tan(math.radians(point.lat))) / math.pi) / 2
    y = min(scale - 1, max(0, int(mercator_y * scale)))
    return (x // TILE_SIZE, y // TILE_SIZE), x % TILE_SIZE, y % TILE_SIZE


def terrain_resolution(points: tuple[Point, ...]) -> float:
    """Largest nominal pixel spacing, not DEM source resolution or vertical accuracy."""
    return float(
        max(156543.03392804097 * math.cos(math.radians(p.lat)) / 2**TERRAIN_ZOOM for p in points)
    )
