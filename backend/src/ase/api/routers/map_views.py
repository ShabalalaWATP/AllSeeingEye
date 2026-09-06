"""Saved report maps, with each edit creating a separately addressable revision."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, SessionDep, get_current_user
from ase.api.schemas_map_views import (
    MapViewCreateIn,
    MapViewPageOut,
    MapViewUpdateIn,
    SavedMapViewOut,
)

router = APIRouter(prefix="/map/views", tags=["maps"], dependencies=[Depends(get_current_user)])


@router.get("")
async def list_views(
    report_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> MapViewPageOut:
    page = await container.saved_map_views(session).list(claims, report_id, limit, offset)
    response.headers["Cache-Control"] = "no-store"
    return MapViewPageOut.build(page)


@router.post("", status_code=201)
async def create_view(
    body: MapViewCreateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> SavedMapViewOut:
    view, revision = await container.saved_map_views(session).create(
        claims,
        body.report_id,
        body.version_number,
        body.title,
        body.state.to_domain(),
        context,
    )
    response.headers["Cache-Control"] = "no-store"
    return SavedMapViewOut.build(view, revision)


@router.get("/{view_id}")
async def get_view(
    view_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> SavedMapViewOut:
    view, revision = await container.saved_map_views(session).get(claims, view_id)
    response.headers["Cache-Control"] = "no-store"
    return SavedMapViewOut.build(view, revision)


@router.get("/{view_id}/revisions/{revision_id}")
async def get_revision(
    view_id: UUID,
    revision_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> SavedMapViewOut:
    view, revision = await container.saved_map_views(session).get(claims, view_id, revision_id)
    response.headers["Cache-Control"] = "no-store"
    return SavedMapViewOut.build(view, revision)


@router.patch("/{view_id}")
async def update_view(
    view_id: UUID,
    body: MapViewUpdateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> SavedMapViewOut:
    view, revision = await container.saved_map_views(session).update(
        claims,
        view_id,
        body.base_revision_id,
        body.version_number,
        body.title,
        body.state.to_domain(),
        context,
    )
    response.headers["Cache-Control"] = "no-store"
    return SavedMapViewOut.build(view, revision)


@router.delete("/{view_id}", status_code=204)
async def archive_view(
    view_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
) -> Response:
    await container.saved_map_views(session).archive(claims, view_id, context)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
