"""Authenticated team board endpoints with server-side membership checks."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_team_board import (
    TeamBoardPageOut,
    TeamBoardPinIn,
    TeamBoardPostIn,
    TeamBoardPostOut,
    TeamBoardPostUpdateIn,
)

router = APIRouter(prefix="/teams/{team_id}/board", tags=["team-board"])


@router.get("/posts")
async def list_posts(
    team_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> TeamBoardPageOut:
    page = await container.team_board(session).list(user, team_id, limit, offset)
    response.headers["Cache-Control"] = "no-store"
    return TeamBoardPageOut.from_page(page)


@router.post("/posts", status_code=201)
async def create_post(
    team_id: UUID,
    body: TeamBoardPostIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TeamBoardPostOut:
    post = await container.team_board(session).create(
        user, team_id, body.text, body.parent_id, context
    )
    author = await container.repositories(session).users.get_by_id(post.author_id)
    return TeamBoardPostOut.from_post(post, author.display_name if author else "Unknown operator")


@router.patch("/posts/{post_id}")
async def edit_post(
    team_id: UUID,
    post_id: UUID,
    body: TeamBoardPostUpdateIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TeamBoardPostOut:
    post = await container.team_board(session).edit(
        user, team_id, post_id, body.text, body.expected_revision, context
    )
    author = await container.repositories(session).users.get_by_id(post.author_id)
    return TeamBoardPostOut.from_post(post, author.display_name if author else "Unknown operator")


@router.delete("/posts/{post_id}", status_code=204, response_class=Response)
async def delete_post(
    team_id: UUID,
    post_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    expected_revision: Annotated[int, Query(ge=1)],
) -> Response:
    await container.team_board(session).delete(user, team_id, post_id, expected_revision, context)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.post("/posts/{post_id}/pin")
async def pin_post(
    team_id: UUID,
    post_id: UUID,
    body: TeamBoardPinIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TeamBoardPostOut:
    post = await container.team_board(session).pin(
        user, team_id, post_id, body.pinned, body.expected_revision, context
    )
    author = await container.repositories(session).users.get_by_id(post.author_id)
    return TeamBoardPostOut.from_post(post, author.display_name if author else "Unknown operator")
