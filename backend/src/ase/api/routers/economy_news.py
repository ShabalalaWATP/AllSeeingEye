"""Authenticated economic headlines and explicit durable briefing admission."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel, ConfigDict

from ase.api.deps import ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.routers.daily_briefing import DailyBriefingOut
from ase.api.schemas_report_jobs import public_job
from ase.api.session_fence import FenceDep
from ase.domain.economy_news import EconomyRegion, PublisherViewpoint
from ase.domain.economy_periods import EconomyWindowDays

router = APIRouter(prefix="/economy", tags=["economy"])


class EconomyNewsItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    url: str
    source_id: str
    source_name: str
    organisation: str
    published_at: datetime
    region_codes: list[Literal["GB", "US", "RU", "CN", "IR"]]
    viewpoint: PublisherViewpoint
    relevance: str


class EconomyNewsOut(BaseModel):
    items: list[EconomyNewsItemOut]
    as_of: datetime
    window_hours: int
    coverage_note: str
    considered: int
    passed: int


class EconomyBriefingOut(DailyBriefingOut):
    window_days: EconomyWindowDays
    period_from: datetime
    period_to: datetime


@router.get("/news")
async def economic_news(
    user: CurrentUser,
    container: ContainerDep,
    fence: FenceDep,
    response: Response,
    region: EconomyRegion = "WORLD",
    limit: Annotated[int, Query(ge=1, le=100)] = 60,
    days: EconomyWindowDays = EconomyWindowDays.TWO,
) -> EconomyNewsOut:
    result = await container.economy_news.read(region, limit, days)
    async with container.source_admission.guard():
        result = await container.economy_news.refilter(result)
        await fence.confirm()
        fence.assert_live()
        response.headers["Cache-Control"] = "private, no-store"
        return EconomyNewsOut(
            items=[EconomyNewsItemOut.model_validate(row) for row in result.items],
            as_of=result.as_of,
            window_hours=result.window_hours,
            coverage_note=result.coverage_note,
            considered=result.considered,
            passed=result.passed,
        )


@router.post("/briefing", status_code=202)
async def economic_briefing(
    user: CurrentUser,
    container: ContainerDep,
    fence: FenceDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
    days: EconomyWindowDays = EconomyWindowDays.TWO,
) -> EconomyBriefingOut:
    result = await container.economy_briefing(session, days).ensure(
        user,
        context,
        check_session=fence.confirm,
    )
    response.headers["Cache-Control"] = "private, no-store"
    fence.assert_live()
    return EconomyBriefingOut(
        job=public_job(result.job),
        next_refresh_at=result.next_refresh_at,
        coverage_note=result.coverage_note,
        window_days=days,
        period_from=result.job["period_from"],
        period_to=result.job["period_to"],
    )
