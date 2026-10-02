"""Scoped forecasts awaiting review and counts by frozen original PHIA band."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, SessionDep, get_current_user
from ase.api.schemas_report_ledgers import ForecastWatchPageOut
from ase.api.session_fence import FenceDep
from ase.container.report_ledgers import report_ledgers
from ase.domain.forecast_views import ForecastCounts

router = APIRouter(
    prefix="/forecasts", tags=["forecasts"], dependencies=[Depends(get_current_user)]
)


@router.get("/watches")
async def watches(
    claims: ClaimsDep,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    team_id: UUID | None = None,
    personal: bool = False,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> ForecastWatchPageOut:
    items, total = await report_ledgers(container, session).watches(
        claims,
        team_id,
        personal,
        limit,
        offset,
    )
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return ForecastWatchPageOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/counts")
async def counts(
    since: datetime,
    until: datetime,
    claims: ClaimsDep,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    team_id: UUID | None = None,
    personal: bool = False,
) -> ForecastCounts:
    result = await report_ledgers(container, session).counts(
        claims, team_id, personal, since, until
    )
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return result
