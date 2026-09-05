"""Search saved reports with embeddings; indexing is an explicit bounded action."""

from fastapi import APIRouter

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.schemas_report_search import (
    ReportSearchHitOut,
    ReportSearchIn,
    ReportSearchOut,
    ReportSearchStatusOut,
)
from ase.api.schemas_reports import ReportSummaryOut

router = APIRouter(prefix="/report-search", tags=["reports"])


@router.get("")
async def search_status(
    user: CurrentUser, session: SessionDep, container: ContainerDep
) -> ReportSearchStatusOut:
    return ReportSearchStatusOut.model_validate(await container.report_search(session).status(user))


@router.post("/index")
async def index_reports(
    user: CurrentUser, session: SessionDep, container: ContainerDep
) -> ReportSearchStatusOut:
    return ReportSearchStatusOut.model_validate(await container.report_search(session).index(user))


@router.post("/query")
async def search_reports(
    body: ReportSearchIn, user: CurrentUser, session: SessionDep, container: ContainerDep
) -> ReportSearchOut:
    result = await container.report_search(session).query(user, body.query, body.limit)
    return ReportSearchOut(
        items=[
            ReportSearchHitOut(report=ReportSummaryOut.from_record(hit.report), score=hit.score)
            for hit in result.items
        ],
        indexed=result.indexed,
        total=result.total,
    )
