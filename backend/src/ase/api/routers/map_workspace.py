"""Personal and team dashboard map documents."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, SessionDep, get_current_user
from ase.api.schemas_map_workspace import (
    MapWorkspaceCreateIn,
    MapWorkspaceOut,
    MapWorkspaceUpdateIn,
)
from ase.domain.map_workspace import WorkspaceKind

router = APIRouter(
    prefix="/map/workspaces", tags=["maps"], dependencies=[Depends(get_current_user)]
)


@router.get("")
async def list_documents(
    kind: WorkspaceKind,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> list[MapWorkspaceOut]:
    documents = await container.map_workspace(session).list(claims, kind, limit, offset)
    response.headers["Cache-Control"] = "no-store"
    return [MapWorkspaceOut.model_validate(document) for document in documents]


@router.get("/{document_id}")
async def get_document(
    document_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> MapWorkspaceOut:
    document = await container.map_workspace(session).get(claims, document_id)
    response.headers["Cache-Control"] = "no-store"
    return MapWorkspaceOut.model_validate(document)


@router.post("", status_code=201)
async def create_document(
    body: MapWorkspaceCreateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> MapWorkspaceOut:
    document = await container.map_workspace(session).create(
        claims, body.kind, body.title, body.payload, body.team_id, context
    )
    response.headers["Cache-Control"] = "no-store"
    return MapWorkspaceOut.model_validate(document)


@router.patch("/{document_id}")
async def update_document(
    document_id: UUID,
    body: MapWorkspaceUpdateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> MapWorkspaceOut:
    document = await container.map_workspace(session).update(
        claims, document_id, body.title, body.payload, body.expected_revision, context
    )
    response.headers["Cache-Control"] = "no-store"
    return MapWorkspaceOut.model_validate(document)


@router.delete("/{document_id}", status_code=204)
async def remove_document(
    document_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
) -> Response:
    await container.map_workspace(session).remove(claims, document_id, context)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
