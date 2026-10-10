"""Search saved reports with embeddings; indexing is an explicit bounded action."""

from functools import partial

from fastapi import APIRouter

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_report_search import (
    ReportSearchHitOut,
    ReportSearchIn,
    ReportSearchOut,
    ReportSearchStatusOut,
)
from ase.api.schemas_reports import ReportSummaryOut
from ase.api.session_fence import FenceDep

router = APIRouter(prefix="/report-search", tags=["reports"])


@router.get("")
async def search_status(
    user: CurrentUser, session: SessionDep, container: ContainerDep, fence: FenceDep
) -> ReportSearchStatusOut:
    result = await container.report_search(session).status(user)
    return await fence.release(ReportSearchStatusOut.model_validate(result), session=session)


@router.post("/index")
async def index_reports(
    user: CurrentUser, session: SessionDep, container: ContainerDep, fence: FenceDep
) -> ReportSearchStatusOut:
    result = await container.report_search(session).index(
        user, before_save=partial(fence.confirm, session=session)
    )
    return await fence.release(ReportSearchStatusOut.model_validate(result), session=session)


@router.post("/query")
async def search_reports(
    body: ReportSearchIn,
    user: CurrentUser,
    session: SessionDep,
    container: ContainerDep,
    fence: FenceDep,
) -> ReportSearchOut:
    result = await container.report_search(session).query(user, body.query, body.limit)
    response = ReportSearchOut(
        items=[
            ReportSearchHitOut(report=ReportSummaryOut.from_record(hit.report), score=hit.score)
            for hit in result.items
        ],
        indexed=result.indexed,
        total=result.total,
    )
    return await fence.release(response, session=session)
