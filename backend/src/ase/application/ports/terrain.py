"""Public elevation-grid boundary, no private planning records are persisted."""

from typing import Protocol

from ase.domain.events import Point


class TerrainGateway(Protocol):
    async def elevations(self, positions: tuple[Point, ...]) -> tuple[float, ...]: ...
