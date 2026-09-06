"""Team management; the application service enforces account and membership authority."""

from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.team_schemas import (
    MemberIn,
    MemberOut,
    MembershipOut,
    TeamDetailOut,
    TeamIn,
    TeamOut,
    TeamsOut,
    TeamUpdateIn,
)

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("")
async def list_teams(user: CurrentUser, session: SessionDep, container: ContainerDep) -> TeamsOut:
    items = await container.teams(session).list_teams(user)
    return TeamsOut(items=[TeamOut.model_validate(team) for team in items])


@router.post("", status_code=201)
async def create_team(
    body: TeamIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TeamOut:
    team = await container.teams(session).create(user, body.name, context)
    return TeamOut.model_validate(team)


@router.get("/{team_id}")
async def get_team(
    team_id: UUID, user: CurrentUser, session: SessionDep, container: ContainerDep
) -> TeamDetailOut:
    team, members = await container.teams(session).roster(user, team_id)
    return TeamDetailOut(
        team=TeamOut.model_validate(team),
        members=[MemberOut.model_validate(member) for member in members],
    )


@router.patch("/{team_id}")
async def update_team(
    team_id: UUID,
    body: TeamUpdateIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> TeamOut:
    team = await container.teams(session).update(
        user, team_id, name=body.name, is_active=body.is_active, context=context
    )
    return TeamOut.model_validate(team)


@router.put("/{team_id}/members")
async def set_member(
    team_id: UUID,
    body: MemberIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> MembershipOut:
    member = await container.teams(session).set_member(
        user, team_id, email=str(body.email), role=body.role, context=context
    )
    return MembershipOut.model_validate(member)


@router.delete("/{team_id}/members/{user_id}", status_code=204, response_class=Response)
async def remove_member(
    team_id: UUID,
    user_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.teams(session).remove_member(user, team_id, user_id, context)
    return Response(status_code=204)
