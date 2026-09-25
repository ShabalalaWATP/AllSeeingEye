"""Authenticated, explicit place lookup; search text never enters access-log URLs."""

import asyncio

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from ase.api.deps import ContainerDep, CurrentUser
from ase.api.session_fence import FenceDep
from ase.domain.errors import InvalidRequest

router = APIRouter()


class NavigationPlaceSearchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=3, max_length=200)


class NavigationPlaceOut(BaseModel):
    label: str = Field(min_length=1, max_length=1000)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


@router.post(
    "/places",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": NavigationPlaceSearchIn.model_json_schema()}
            },
        }
    },
)
async def search_places(
    user: CurrentUser,
    container: ContainerDep,
    fence: FenceDep,
    request: Request,
    response: Response,
) -> list[NavigationPlaceOut]:
    await fence.confirm()
    if request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
        raise InvalidRequest("Send place searches as JSON.")
    raw = bytearray()
    try:
        async with asyncio.timeout(5):
            async for chunk in request.stream():
                if len(raw) + len(chunk) > 2048:
                    raise InvalidRequest("Place search exceeds the input limit.")
                raw.extend(chunk)
        body = NavigationPlaceSearchIn.model_validate_json(raw)
    except (ValueError, TimeoutError):
        raise InvalidRequest("Enter a place name between 3 and 200 characters.") from None
    finally:
        raw.clear()
    await fence.confirm()
    results = await container.place_search.search(user.id, body.query)
    await fence.confirm()
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return [
        NavigationPlaceOut(label=row.label, lat=row.point.lat, lon=row.point.lon) for row in results
    ]
