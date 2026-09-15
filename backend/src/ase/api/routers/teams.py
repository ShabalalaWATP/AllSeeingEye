"""Team management; the application service enforces account and membership authority."""

from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_ai_usage import TeamAiUsageOut
from ase.api.team_schemas import (
    MemberIn,
    MemberOut,
    MemberRoleIn,
    MembershipOut,
    TeamDetailOut,
    TeamIn,
    TeamOut,
    TeamsOut,
    TeamUpdateIn,
)
from ase.application.teams.service import DESCRIPTION_UNSET

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
    team = await container.teams(session).create(
        user, body.name, context, description=body.description
    )
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


@router.get("/{team_id}/ai-usage")
async def team_ai_usage(
    team_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> TeamAiUsageOut:
    # Members see their own attributed usage, Managers see aggregates and member
    # totals, administrators see any team. Non-members receive 404.
    response.headers["Cache-Control"] = "no-store"
    usage = await container.ai_usage_views(session).team(user, team_id)
    return TeamAiUsageOut.from_usage(usage)


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
        user,
        team_id,
        name=body.name,
        is_active=body.is_active,
        description=(
            body.description if "description" in body.model_fields_set else DESCRIPTION_UNSET
        ),
        context=context,
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


@router.patch("/{team_id}/members/{user_id}")
async def change_member_role(
    team_id: UUID,
    user_id: UUID,
    body: MemberRoleIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> MembershipOut:
    member = await container.teams(session).change_role(user, team_id, user_id, body.role, context)
    return MembershipOut.model_validate(member)


@router.post("/{team_id}/leave", status_code=204, response_class=Response)
async def leave_team(
    team_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
) -> Response:
    await container.teams(session).leave(user, team_id, context)
    return Response(status_code=204)


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
