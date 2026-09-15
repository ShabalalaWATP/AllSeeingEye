"""The bounded team overview; membership is checked in the application layer."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_team_dashboard import TeamDashboardOut

router = APIRouter(prefix="/teams/{team_id}", tags=["team-board"])


@router.get("/dashboard")
async def team_dashboard(
    team_id: UUID,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> TeamDashboardOut:
    dashboard = await container.team_dashboard(session).get(user, team_id)
    response.headers["Cache-Control"] = "no-store"
    return TeamDashboardOut.from_dashboard(dashboard)
