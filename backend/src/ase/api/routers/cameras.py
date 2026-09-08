"""Authenticated catalogue only. Images load directly from approved public providers."""

from fastapi import APIRouter, HTTPException, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser
from ase.api.schemas_cameras import CameraCatalogueOut
from ase.api.session_guard import validate_request_session

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("")
async def camera_catalogue(
    actor: CurrentUser,
    claims: ClaimsDep,
    container: ContainerDep,
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
    await validate_request_session(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return CameraCatalogueOut.model_validate(result)
