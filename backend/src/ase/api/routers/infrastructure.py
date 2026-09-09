"""Authenticated immutable public infrastructure catalogue."""

from fastapi import APIRouter, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser
from ase.api.schemas_infrastructure import InfrastructureOut
from ase.api.session_guard import validate_request_session

router = APIRouter(prefix="/map-infrastructure", tags=["map"])


@router.get("")
async def infrastructure(
    user: CurrentUser, claims: ClaimsDep, response: Response, container: ContainerDep
) -> InfrastructureOut:
    result = InfrastructureOut.model_validate(container.public_infrastructure())
    await validate_request_session(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result
