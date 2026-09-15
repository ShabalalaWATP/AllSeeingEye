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
    TeamBoardReadIn,
    TeamBoardRemoveIn,
    TeamBoardUnreadOut,
)
from ase.container import Container
from ase.domain.team_board import TeamBoardPost

router = APIRouter(prefix="/teams/{team_id}/board", tags=["team-board"])
NO_STORE = {"Cache-Control": "no-store"}


async def _out(container: Container, session: SessionDep, post: TeamBoardPost) -> TeamBoardPostOut:
    author = await container.repositories(session).users.get_by_id(post.author_id)
    return TeamBoardPostOut.from_post(post, author.display_name if author else "Unknown operator")


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
    response.headers.update(NO_STORE)
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
    return await _out(container, session, post)


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
    return await _out(container, session, post)


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
    """Author removal. Moderators use the remove action so a reason stays out of URLs."""
    await container.team_board_moderation(session).remove(
        user, team_id, post_id, expected_revision, None, context
    )
    return Response(status_code=204, headers=NO_STORE)


@router.post("/posts/{post_id}/remove")
async def remove_post(
    team_id: UUID,
    post_id: UUID,
    body: TeamBoardRemoveIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TeamBoardPostOut:
    post = await container.team_board_moderation(session).remove(
        user, team_id, post_id, body.expected_revision, body.reason, context
    )
    return await _out(container, session, post)


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
    post = await container.team_board_moderation(session).pin(
        user, team_id, post_id, body.pinned, body.expected_revision, body.reason, context
    )
    return await _out(container, session, post)


@router.post("/read")
async def mark_read(
    team_id: UUID,
    body: TeamBoardReadIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> TeamBoardUnreadOut:
    unread = await container.team_board(session).mark_read(user, team_id, body.last_seen_post_id)
    response.headers.update(NO_STORE)
    return TeamBoardUnreadOut(unread_count=unread)
