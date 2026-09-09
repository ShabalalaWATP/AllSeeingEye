"""Authenticated explicit DEM request, bounded before JSON parsing."""

import asyncio

from fastapi import APIRouter, Request, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser
from ase.api.schemas_terrain import TerrainElevationsIn, TerrainElevationsOut
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.domain.errors import InvalidRequest
from ase.domain.events import Point
from ase.domain.terrain import terrain_resolution

router = APIRouter(prefix="/terrain", tags=["terrain"])
INPUT_SCHEMA = TerrainElevationsIn.model_json_schema()
INPUT_SCHEMA["properties"]["positions"]["items"] = INPUT_SCHEMA.pop("$defs")["TerrainPositionIn"]
MAX_BODY_BYTES = 64 * 1024


@router.post(
    "/elevations",
    openapi_extra={
        "requestBody": {"required": True, "content": {"application/json": {"schema": INPUT_SCHEMA}}}
    },
)
async def elevations(
    user: CurrentUser,
    claims: ClaimsDep,
    container: ContainerDep,
    request: Request,
    response: Response,
) -> TerrainElevationsOut:
    await validate_request_session(container, claims)
    if request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
        raise InvalidRequest("Send terrain positions as JSON.")
    raw = bytearray()
    try:
        async with asyncio.timeout(5):
            async for chunk in request.stream():
                if len(raw) + len(chunk) > MAX_BODY_BYTES:
                    raise InvalidRequest("Terrain request exceeds the input limit.")
                raw.extend(chunk)
        body = TerrainElevationsIn.model_validate_json(raw)
    except (ValueError, TimeoutError):
        raise InvalidRequest(
            "Use 1 to 1,000 valid positions within the terrain latitude limits."
        ) from None
    finally:
        raw.clear()
    positions = tuple(Point(point.lon, point.lat) for point in body.positions)
    await validate_request_session(container, claims)
    result = await container.terrain_sampler.sample(user.id, positions)
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return TerrainElevationsOut(
        elevations_m=list(result), resolution_m=terrain_resolution(positions)
    )
