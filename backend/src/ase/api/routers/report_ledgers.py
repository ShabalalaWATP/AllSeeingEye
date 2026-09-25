"""Exact-version forecast and indicator ledgers under saved reports."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, SessionDep, get_current_user
from ase.api.schemas_report_ledgers import (
    ForecastCreateIn,
    ForecastReviewIn,
    IndicatorCreateIn,
    MissingReadingIn,
)
from ase.api.session_fence import FenceDep
from ase.container.report_ledgers import report_ledgers
from ase.domain.report_ledgers import ReportLedger

router = APIRouter(
    prefix="/reports/{report_id}/versions/{number}/ledgers",
    tags=["report-ledgers"],
    dependencies=[Depends(get_current_user)],
)
VersionNumber = Annotated[int, Path(ge=1, le=2_147_483_647)]


@router.get("")
async def list_ledgers(
    report_id: UUID,
    number: VersionNumber,
    claims: ClaimsDep,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> dict[str, object]:
    items, total = await report_ledgers(container, session).list(
        claims, report_id, number, limit, offset
    )
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{ledger_id}")
async def get_ledger(
    report_id: UUID,
    number: VersionNumber,
    ledger_id: UUID,
    claims: ClaimsDep,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> ReportLedger:
    result = await report_ledgers(container, session).get(claims, report_id, number, ledger_id)
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.post("/forecasts", status_code=201)
async def create_forecast(
    report_id: UUID,
    number: VersionNumber,
    body: ForecastCreateIn,
    claims: ClaimsDep,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> ReportLedger:
    result = await report_ledgers(container, session).create_forecast(
        claims, report_id, number, body.to_domain(), context
    )
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.post("/indicators", status_code=201)
async def create_indicator(
    report_id: UUID,
    number: VersionNumber,
    body: IndicatorCreateIn,
    claims: ClaimsDep,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> ReportLedger:
    result = await report_ledgers(container, session).create_indicator(
        claims, report_id, number, body.to_domain(), context
    )
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.post("/{ledger_id}/reviews")
async def review_forecast(
    report_id: UUID,
    number: VersionNumber,
    ledger_id: UUID,
    body: ForecastReviewIn,
    claims: ClaimsDep,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> ReportLedger:
    result = await report_ledgers(container, session).decide(
        claims, report_id, number, ledger_id, body.to_domain(), context
    )
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.post("/{ledger_id}/missing-readings")
async def record_missing(
    report_id: UUID,
    number: VersionNumber,
    ledger_id: UUID,
    body: MissingReadingIn,
    claims: ClaimsDep,
    fence: FenceDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> ReportLedger:
    result = await report_ledgers(container, session).record_missing(
        claims, report_id, number, ledger_id, body.to_domain(), context
    )
    fence.assert_live()
    response.headers["Cache-Control"] = "private, no-store"
    return result
