"""Authenticated on-demand radio calculations with bounded request intake."""

import asyncio

from fastapi import APIRouter, Request, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser
from ase.api.schemas_groundwave import GroundwaveIn, GroundwaveOut, GroundwaveSampleOut
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.domain.errors import InvalidRequest
from ase.domain.groundwave import GroundwaveInput

router = APIRouter(prefix="/radio", tags=["radio"])


@router.post(
    "/groundwave",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": GroundwaveIn.model_json_schema()}},
        }
    },
)
async def groundwave(
    user: CurrentUser,
    claims: ClaimsDep,
    container: ContainerDep,
    request: Request,
    response: Response,
) -> GroundwaveOut:
    await validate_request_session(container, claims)
    if request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
        raise InvalidRequest("Send groundwave study inputs as JSON.")
    raw = bytearray()
    try:
        async with asyncio.timeout(5):
            async for chunk in request.stream():
                if len(raw) + len(chunk) > 4096:
                    raise InvalidRequest("Groundwave request exceeds the input limit.")
                raw.extend(chunk)
        body = GroundwaveIn.model_validate_json(raw)
    except (ValueError, TimeoutError):
        raise InvalidRequest(
            "Use valid HF groundwave inputs within the displayed model bounds."
        ) from None
    finally:
        raw.clear()
    await validate_request_session(container, claims)
    samples = await container.groundwave_study.calculate(
        user.id, GroundwaveInput(**body.model_dump())
    )
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return GroundwaveOut(samples=[GroundwaveSampleOut.model_validate(sample) for sample in samples])
