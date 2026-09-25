"""Authenticated catalogue only. Images load directly from approved public providers, except
the few providers that serve images inline; those frames are relayed here, one per request."""

import re

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import Response as RawResponse

from ase.api.deps import ContainerDep, CurrentUser
from ase.api.schemas_cameras import CameraCatalogueOut
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/cameras", tags=["cameras"])
PROVIDER_ID = re.compile(r"[a-z][a-z0-9-]{0,39}")
FRAME_ID = re.compile(r"[A-Za-z0-9_-]{1,40}")


@router.get("/frames/{provider}/{frame_id}.jpg")
async def camera_frame(
    provider: str,
    frame_id: str,
    actor: CurrentUser,
    container: ContainerDep,
    fence: FenceDep,
) -> RawResponse:
    """A JPEG relayed from a fixed provider endpoint for a camera in its last index."""
    if (
        PROVIDER_ID.fullmatch(provider) is None
        or FRAME_ID.fullmatch(frame_id) is None
        or provider not in container.cameras.provider_ids
    ):
        raise HTTPException(status_code=404, detail="Unknown camera frame")
    try:
        data = await container.cameras.frame(actor, provider, frame_id)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail="Camera frame unavailable") from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=503, detail="Camera frame unavailable") from exc
    if data is None:
        raise HTTPException(status_code=404, detail="Unknown camera frame")
    await fence.confirm()
    return RawResponse(
        content=data,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=30", "X-Content-Type-Options": "nosniff"},
    )


@router.get("")
async def camera_catalogue(
    actor: CurrentUser,
    container: ContainerDep,
    fence: FenceDep,
    response: Response,
    provider: str | None = Query(default=None, max_length=100),
) -> CameraCatalogueOut:
    try:
        if provider:
            result = await container.cameras.catalogue(actor, provider)
        else:
            result = await container.cameras.initial_catalogue(actor)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Unknown camera provider") from exc
    await fence.confirm()
    response.headers["Cache-Control"] = "private, no-store"
    return CameraCatalogueOut.model_validate(result)
