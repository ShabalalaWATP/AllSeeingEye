"""Authenticated team invitation endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_team_invitations import (
    TeamInvitationActionIn,
    TeamInvitationCreateIn,
    TeamInvitationOut,
    TeamInvitationPageOut,
)
from ase.domain.team_invitation import InvitationStatus

router = APIRouter(tags=["team-invitations"])


@router.get("/me/team-invitations", response_model=TeamInvitationPageOut)
async def my_invitations(
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    status: InvitationStatus | None = InvitationStatus.PENDING,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> TeamInvitationPageOut:
    page = await container.team_invitations(session).inbox(
        actor, status=status, limit=limit, offset=offset
    )
    return TeamInvitationPageOut.from_page(page)


@router.get("/teams/{team_id}/invitations", response_model=TeamInvitationPageOut)
async def list_team_invitations(
    team_id: UUID,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    status: InvitationStatus | None = InvitationStatus.PENDING,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> TeamInvitationPageOut:
    page = await container.team_invitations(session).team_inbox(
        actor, team_id, status=status, limit=limit, offset=offset
    )
    return TeamInvitationPageOut.from_page(page)


@router.post("/teams/{team_id}/invitations", status_code=201, response_model=TeamInvitationOut)
async def send_team_invitation(
    team_id: UUID,
    body: TeamInvitationCreateIn,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TeamInvitationOut:
    invitation = await container.team_invitations(session).send(
        actor, team_id, body.recipient_id, body.note, context
    )
    return TeamInvitationOut.from_entity(invitation)


@router.delete(
    "/teams/{team_id}/invitations/{invitation_id}", status_code=204, response_class=Response
)
async def withdraw_team_invitation(
    team_id: UUID,
    invitation_id: UUID,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    expected_revision: Annotated[int | None, Query(ge=1)] = None,
) -> Response:
    await container.team_invitations(session).withdraw(
        actor, team_id, invitation_id, context, expected_revision
    )
    return Response(status_code=204)


@router.post(
    "/me/team-invitations/{invitation_id}/accept",
    response_model=TeamInvitationOut,
)
async def accept_team_invitation(
    invitation_id: UUID,
    body: TeamInvitationActionIn,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TeamInvitationOut:
    invitation = await container.team_invitations(session).accept(
        actor, invitation_id, context, body.expected_revision
    )
    return TeamInvitationOut.from_entity(invitation)


@router.post(
    "/me/team-invitations/{invitation_id}/decline",
    response_model=TeamInvitationOut,
)
async def decline_team_invitation(
    invitation_id: UUID,
    body: TeamInvitationActionIn,
    actor: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TeamInvitationOut:
    invitation = await container.team_invitations(session).decline(
        actor, invitation_id, context, body.expected_revision
    )
    return TeamInvitationOut.from_entity(invitation)
