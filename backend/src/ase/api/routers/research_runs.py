"""Authenticated progress reads for an existing synchronous research request."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from ase.api.deps import ContainerDep, CurrentUser
from ase.domain.research_runs import ResearchStage

router = APIRouter(prefix="/research/runs", tags=["research"])


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
