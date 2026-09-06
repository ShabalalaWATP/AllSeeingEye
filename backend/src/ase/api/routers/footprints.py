"""Explicit authenticated catalogue requests; no imagery fetch or shared persistence."""

from fastapi import APIRouter, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, CurrentUser
from ase.api.schemas_footprints import FootprintCollectionOut, FootprintSearchIn
from ase.api.session_guard import validate_request_session

router = APIRouter(prefix="/research/footprints", tags=["research"])


@router.post("")
async def search_footprints(
    body: FootprintSearchIn,
    actor: CurrentUser,
    claims: ClaimsDep,
    context: ContextDep,
    container: ContainerDep,
    response: Response,
) -> FootprintCollectionOut:
    async def revalidate() -> None:
        await validate_request_session(container, claims)

    result = await container.footprints.execute(actor, body.to_query(), context, revalidate)
    response.headers["Cache-Control"] = "no-store"
    return FootprintCollectionOut.from_domain(result)
