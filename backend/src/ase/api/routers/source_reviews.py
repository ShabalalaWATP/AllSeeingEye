"""Owner/team authorised reviewer history, separate from original report exports."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, SessionDep, get_current_user
from ase.api.schemas_source_reviews import SourceReviewIn, SourceSnapshotIn
from ase.container.source_reviews import source_reviews
from ase.domain.source_review_records import SourceReviewSnapshot
from ase.domain.source_reviews import SourceReviewKind, SourceReviewRevision

router = APIRouter(
    prefix="/reports/{report_id}/versions/{number}",
    tags=["source-reviews"],
    dependencies=[Depends(get_current_user)],
)
VersionNumber = Annotated[int, Path(ge=1, le=2_147_483_647)]
ScopeText = Annotated[str, Query(min_length=1, max_length=200)]


@router.get("/source-reviews")
async def history(
    report_id: UUID,
    number: VersionNumber,
    label: ScopeText,
    judgement_id: ScopeText,
    subject: ScopeText,
    kind: SourceReviewKind,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> tuple[SourceReviewRevision, ...]:
    result = await source_reviews(container, session).history(
        claims, report_id, number, label, judgement_id, subject, kind
    )
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.post("/source-reviews", status_code=201)
async def review(
    report_id: UUID,
    number: VersionNumber,
    body: SourceReviewIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> SourceReviewRevision:
    result = await source_reviews(container, session).review(
        claims, report_id, number, body.to_domain(), context
    )
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.post("/source-assessment-snapshots", status_code=201)
async def freeze(
    report_id: UUID,
    number: VersionNumber,
    body: SourceSnapshotIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> SourceReviewSnapshot:
    result = await source_reviews(container, session).freeze(
        claims, report_id, number, body.subjects, context
    )
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.get("/source-assessment-snapshots/{snapshot_id}")
async def snapshot(
    report_id: UUID,
    number: VersionNumber,
    snapshot_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> SourceReviewSnapshot:
    result = await source_reviews(container, session).snapshot(
        claims, report_id, number, snapshot_id
    )
    response.headers["Cache-Control"] = "private, no-store"
    return result
