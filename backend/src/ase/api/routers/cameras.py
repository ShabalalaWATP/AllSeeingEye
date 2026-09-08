"""Authenticated catalogue only. Images load directly from approved public providers."""

from fastapi import APIRouter, Response

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
) -> CameraCatalogueOut:
    result = await container.cameras.catalogue(actor)
    await validate_request_session(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return CameraCatalogueOut.model_validate(result)
