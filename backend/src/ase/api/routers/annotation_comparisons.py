"""Private explicit comparison previews and replayable exact-selection JSON manifests."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, SessionDep, get_current_user
from ase.api.schemas_annotation_comparisons import (
    AnnotationComparisonExportIn,
    AnnotationComparisonIn,
    AnnotationComparisonOut,
    ComparisonReportsOut,
)
from ase.api.schemas_reports import ReportSummaryOut
from ase.api.session_guard import validate_request_session

router = APIRouter(
    prefix="/annotation-comparisons",
    tags=["annotation-comparisons"],
    dependencies=[Depends(get_current_user)],
)


@router.post("")
async def preview_annotation_comparison(
    body: AnnotationComparisonIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> AnnotationComparisonOut:
    result = await container.annotation_comparisons(session).execute(claims, body.to_domain())
    await validate_request_session(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return AnnotationComparisonOut(result)


@router.post("/export", response_class=Response)
async def export_annotation_comparison(
    body: AnnotationComparisonExportIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
) -> Response:
    result = await container.annotation_comparisons(session).execute(
        claims, body.to_domain(), body.expected_comparison_sha256
    )
    await validate_request_session(container, claims)
    return Response(
        result.content,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/reports")
async def comparison_reports(
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    q: Annotated[str, Query(max_length=120)] = "",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
) -> ComparisonReportsOut:
    records, total = await container.comparison_reports(session).execute(claims, q, limit, offset)
    await validate_request_session(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return ComparisonReportsOut(
        items=[ReportSummaryOut.from_record(row) for row in records],
        total=total,
        offset=offset,
        limit=limit,
    )
