"""Explicit, idempotent admission of the caller's daily global situation briefing."""

from datetime import datetime

from fastapi import APIRouter, Response
from pydantic import BaseModel

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_report_jobs import ReportJobOut, public_job
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/live-monitor", tags=["live-monitor"])


class DailyBriefingOut(BaseModel):
    job: ReportJobOut
    next_refresh_at: datetime
    coverage_note: str


@router.post("/briefing", status_code=202)
async def ensure_briefing(
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> DailyBriefingOut:
    result = await container.daily_briefing(session).ensure(
        user,
        context,
        check_session=fence.confirm,
    )
    response.headers["Cache-Control"] = "private, no-store"
    payload = DailyBriefingOut(
        job=public_job(result.job),
        next_refresh_at=result.next_refresh_at,
        coverage_note=result.coverage_note,
    )
    fence.assert_live()
    return payload
