"""Base-map tiles proxied through the API so the Ordnance Survey key stays server-side."""

from __future__ import annotations

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, CurrentUser
from ase.api.errors import InvalidQuery, UpstreamUnavailable
from ase.application.ports.tiles import TileUpstreamError, is_valid_os_tile
from ase.domain.errors import NotFound, RateLimited

router = APIRouter(prefix="/tiles", tags=["tiles"])

# Tiles change rarely; the browser may keep them for a day without asking again.
TILE_CACHE_CONTROL = "private, max-age=86400"


@router.get("/os/{layer}/{z}/{x}/{y}.png", response_class=Response)
async def os_tile(
    user: CurrentUser, container: ContainerDep, layer: str, z: int, x: int, y: int
) -> Response:
    if not container.tiles.configured:
        raise NotFound("OS Maps tiles are not configured on this server.")
    if not is_valid_os_tile(layer, z, x, y):
        raise InvalidQuery(fields={"tile": "Unknown OS layer or tile address."})
    retry = container.limiter.hit(f"os-maps:user:{user.id}", 120, 60)
    if retry is not None:
        raise RateLimited(retry)
    try:
        tile = await container.tiles.fetch(layer, z, x, y)
    except TileUpstreamError as exc:
        if exc.status == 404:
            raise NotFound("No tile at this address.") from exc
        raise UpstreamUnavailable(f"The tile server answered {exc.status}.") from exc
    return Response(
        content=tile.content,
        media_type=tile.content_type,
        headers={"Cache-Control": TILE_CACHE_CONTROL},
    )
