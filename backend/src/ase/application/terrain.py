"""Explicit terrain batches with bounded public-provider work and no queued users."""

import asyncio
from uuid import UUID

from ase.application.ports.services import RateLimiter
from ase.application.ports.terrain import TerrainGateway
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.events import Point
from ase.domain.terrain import MAX_TERRAIN_POSITIONS, MAX_TERRAIN_TILES, terrain_pixel


class TerrainSampler:
    def __init__(self, gateway: TerrainGateway, limiter: RateLimiter) -> None:
        self._gateway, self._limiter = gateway, limiter
        self._active = 0

    async def sample(self, actor_id: UUID, positions: tuple[Point, ...]) -> tuple[float, ...]:
        if not 1 <= len(positions) <= MAX_TERRAIN_POSITIONS:
            raise InvalidRequest("Choose between 1 and 1,000 terrain samples.")
        try:
            tiles = {terrain_pixel(point)[0] for point in positions}
        except ValueError:
            raise InvalidRequest(
                "Terrain sampling is limited to latitudes within 85.05°."
            ) from None
        if len(tiles) > MAX_TERRAIN_TILES:
            raise InvalidRequest("Terrain request covers too many tiles. Reduce the study area.")
        retry = self._limiter.hit(f"terrain:{actor_id}", 6, 60)
        if retry is not None:
            raise RateLimited(retry)
        if self._active >= 2:
            raise RateLimited(2)
        retry = self._limiter.hit("terrain:provider", 12, 60)
        if retry is not None:
            raise RateLimited(retry)
        self._active += 1
        try:
            async with asyncio.timeout(30):
                result = await self._gateway.elevations(positions)
                if len(result) != len(positions):
                    raise ValueError("Incomplete terrain batch")
                return result
        except Exception:
            raise InvalidRequest(
                "Terrain data unavailable for this area. "
                "No missing heights were replaced with zero. "
                "Try a smaller area or retry later."
            ) from None
        finally:
            self._active -= 1
