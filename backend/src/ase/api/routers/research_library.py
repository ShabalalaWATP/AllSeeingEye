"""Only the bearer user's annotations, intersected with current report visibility."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, SessionDep
from ase.api.schemas_library import LibraryPageOut, LibraryPreferenceIn, LibraryPreferenceOut

router = APIRouter(prefix="/me/library", tags=["me"])


@router.get("")
async def list_library(
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
    favourite_only: bool = False,
    tag: Annotated[str | None, Query(min_length=1, max_length=40)] = None,
) -> LibraryPageOut:
    result = await container.research_library(session).list(
        claims, limit, offset, favourite_only, tag
    )
    response.headers["Cache-Control"] = "no-store"
    return LibraryPageOut.build(result)


@router.get("/{report_id}")
async def get_library_preference(
    report_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> LibraryPreferenceOut:
    result = await container.research_library(session).get(claims, report_id)
    response.headers["Cache-Control"] = "no-store"
    return LibraryPreferenceOut.model_validate(result)


@router.put("/{report_id}")
async def save_library_preference(
    report_id: UUID,
    body: LibraryPreferenceIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> LibraryPreferenceOut:
    result = await container.research_library(session).save(
        claims, report_id, body.to_domain(), context
    )
    response.headers["Cache-Control"] = "no-store"
    return LibraryPreferenceOut.model_validate(result)


@router.delete("/{report_id}", status_code=204)
async def remove_library_preference(
    report_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
) -> Response:
    await container.research_library(session).remove(claims, report_id, context)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
