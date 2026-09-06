"""Authenticated progress reads for an existing synchronous research request."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Response
from pydantic import BaseModel

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_map_origin import MapResearchOriginOut
from ase.api.schemas_research_plan import ResearchPlanIn, ResearchPreviewOut
from ase.domain.research_runs import ResearchStage

router = APIRouter(prefix="/research/runs", tags=["research"])


@router.post("/plan")
async def preview_plan(
    body: ResearchPlanIn,
    user: CurrentUser,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> ResearchPreviewOut:
    preview = await container.preview_research(session).execute(
        user,
        body.to_query(),
        map_view_id=body.map_view_id,
        map_revision_id=body.map_revision_id,
        team_id=body.team_id,
    )
    response.headers["Cache-Control"] = "no-store"
    result = ResearchPreviewOut.model_validate(preview.plan)
    result.map_origin = (
        MapResearchOriginOut.model_validate(preview.map_origin) if preview.map_origin else None
    )
    return result


class ResearchRunOut(BaseModel):
    id: UUID
    stage: ResearchStage
    started_at: datetime
    updated_at: datetime
    expires_at: datetime
    report_id: UUID | None


@router.get("/{run_id}")
async def get_research_run(
    run_id: UUID, user: CurrentUser, container: ContainerDep
) -> ResearchRunOut:
    run = container.research_runs.read(user, run_id)
    return ResearchRunOut(
        id=run.id,
        stage=run.stage,
        started_at=run.started_at,
        updated_at=run.updated_at,
        expires_at=run.expires_at,
        report_id=run.report_id,
    )
