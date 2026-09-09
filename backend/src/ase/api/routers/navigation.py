"""Authenticated route estimates, only on an explicit bounded POST."""

import asyncio

from fastapi import APIRouter, Request, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser
from ase.api.schemas_navigation import (
    NavigationCapabilitiesOut,
    NavigationRouteIn,
    NavigationRouteOut,
    NavigationStepOut,
    navigation_capabilities,
)
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.domain.errors import InvalidRequest
from ase.domain.events import Point

router = APIRouter(prefix="/navigation", tags=["navigation"])
INPUT_SCHEMA = NavigationRouteIn.model_json_schema()
INPUT_SCHEMA["properties"]["waypoints"]["items"] = INPUT_SCHEMA.pop("$defs")["NavigationPointIn"]


@router.get("/capabilities")
async def capabilities(user: CurrentUser, container: ContainerDep) -> NavigationCapabilitiesOut:
    return navigation_capabilities(container.settings.feeds_contact)


@router.post(
    "/route",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": INPUT_SCHEMA}},
        }
    },
)
async def calculate_route(
    user: CurrentUser,
    claims: ClaimsDep,
    container: ContainerDep,
    request: Request,
    response: Response,
) -> NavigationRouteOut:
    # Authenticate before body intake. Bound bytes as well as waypoint counts.
    await validate_request_session(container, claims)
    capability = navigation_capabilities(container.settings.feeds_contact)
    if not capability.available:
        raise InvalidRequest(capability.configuration_message)
    if request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
        raise InvalidRequest("Send route waypoints as JSON.")
    raw = bytearray()
    try:
        async with asyncio.timeout(5):
            async for chunk in request.stream():
                if len(raw) + len(chunk) > 4096:
                    raise InvalidRequest("Route request exceeds the input limit.")
                raw.extend(chunk)
        body = NavigationRouteIn.model_validate_json(raw)
    except (ValueError, TimeoutError):
        raise InvalidRequest(
            "Use two to eight valid route waypoints and a supported mode."
        ) from None
    finally:
        raw.clear()
    await validate_request_session(container, claims)
    result = await container.route_planner.calculate(
        user.id, body.mode, tuple(Point(point.lon, point.lat) for point in body.waypoints)
    )
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return NavigationRouteOut(
        mode=result.mode,
        distance_km=result.distance_km,
        duration_seconds=result.duration_seconds,
        coordinates=[(point.lon, point.lat) for point in result.coordinates],
        steps=[
            NavigationStepOut(
                instruction=step.instruction,
                distance_km=step.distance_km,
                duration_seconds=step.duration_seconds,
            )
            for step in result.steps
        ],
    )
