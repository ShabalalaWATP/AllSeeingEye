"""Authenticated, opt-in operator directory and the current user's directory profile."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_directory_profile import (
    DirectoryPageOut,
    DirectoryProfileOut,
    DirectoryProfileUpdateIn,
)

router = APIRouter(tags=["directory"])


@router.get("/directory/users", response_model=DirectoryPageOut)
async def search_directory(
    actor: CurrentUser,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    q: Annotated[str, Query(min_length=2, max_length=80)],
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> DirectoryPageOut:
    page = await container.directory_profile(session).search(actor, q, limit, offset)
    response.headers["Cache-Control"] = "no-store"
    return DirectoryPageOut.from_page(page)


@router.get("/me/directory-profile", response_model=DirectoryProfileOut)
async def get_directory_profile(
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> DirectoryProfileOut:
    profile = await container.directory_profile(session).get(claims)
    response.headers["Cache-Control"] = "no-store"
    return DirectoryProfileOut.from_entity(profile)


@router.patch("/me/directory-profile", response_model=DirectoryProfileOut)
async def update_directory_profile(
    body: DirectoryProfileUpdateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> DirectoryProfileOut:
    profile = await container.directory_profile(session).update(
        claims,
        body.to_changes(),
        body.expected_revision,
        context,
    )
    response.headers["Cache-Control"] = "no-store"
    return DirectoryProfileOut.from_entity(profile)
