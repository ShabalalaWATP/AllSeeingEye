"""Explicit authenticated catalogue requests; no imagery fetch or shared persistence."""

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, ContextDep, CurrentUser
from ase.api.schemas_footprints import FootprintCollectionOut, FootprintSearchIn
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/research/footprints", tags=["research"])


@router.post("")
async def search_footprints(
    body: FootprintSearchIn,
    actor: CurrentUser,
    context: ContextDep,
    fence: FenceDep,
    container: ContainerDep,
    response: Response,
) -> FootprintCollectionOut:
    async def revalidate() -> None:
        await fence.confirm()

    result = await container.footprints.execute(actor, body.to_query(), context, revalidate)
    response.headers["Cache-Control"] = "no-store"
    return FootprintCollectionOut.from_domain(result)
