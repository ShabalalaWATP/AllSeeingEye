"""Authenticated immutable public infrastructure catalogue."""

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, CurrentUser
from ase.api.schemas_infrastructure import InfrastructureOut

router = APIRouter(prefix="/map-infrastructure", tags=["map"])


@router.get("")
async def infrastructure(
    user: CurrentUser, response: Response, container: ContainerDep
) -> InfrastructureOut:
    response.headers["Cache-Control"] = "private, no-store"
    return InfrastructureOut.model_validate(container.public_infrastructure())
