"""Authenticated immutable public infrastructure catalogue."""

from fastapi import APIRouter, Request, Response

from ase.api.catalogue_responses import catalogue_responses
from ase.api.deps import ContainerDep, CurrentUser
from ase.api.schemas_infrastructure import InfrastructureOut
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/map-infrastructure", tags=["map"])


@router.get("", response_model=InfrastructureOut)
async def infrastructure(
    user: CurrentUser,
    request: Request,
    container: ContainerDep,
    fence: FenceDep,
) -> Response:
    snapshot = container.public_infrastructure()
    result = catalogue_responses.get(
        "/api/map-infrastructure", snapshot, lambda: InfrastructureOut.model_validate(snapshot)
    )
    await fence.confirm()
    return result.response(request.headers.get("if-none-match"))
