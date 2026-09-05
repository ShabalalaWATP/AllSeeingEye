"""Base-map tiles fetched on the browser's behalf so a paid key never leaves the server."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

OS_LAYERS = frozenset({"Road_3857", "Outdoor_3857", "Light_3857"})
OS_MIN_ZOOM = 7
OS_MAX_ZOOM = 16  # zoom 17 to 20 are premium on the OS Data Hub free plan


@dataclass(frozen=True, slots=True)
class Tile:
    content: bytes
    content_type: str


class TileUpstreamError(Exception):
    """The tile server answered with an error status; the status is passed on."""

    def __init__(self, status: int) -> None:
        super().__init__(f"tile upstream answered {status}")
        self.status = status


def is_valid_os_tile(layer: str, z: int, x: int, y: int) -> bool:
    if layer not in OS_LAYERS or not OS_MIN_ZOOM <= z <= OS_MAX_ZOOM:
        return False
    span = 1 << z
    return 0 <= x < span and 0 <= y < span


class TileProvider(Protocol):
    @property
    def configured(self) -> bool:
        """False when no key is set; the API then reports the layer as unavailable."""
        ...

    async def fetch(self, layer: str, z: int, x: int, y: int) -> Tile: ...

    async def aclose(self) -> None: ...
