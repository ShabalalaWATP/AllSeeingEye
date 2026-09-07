"""Scoped operator relationship review and exact revision retrieval."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, SessionDep, get_current_user
from ase.api.schemas_relationships import (
    RelationshipAssertionsOut,
    RelationshipCreateIn,
    RelationshipDetailOut,
    RelationshipPageOut,
    RelationshipUpdateIn,
)
from ase.domain.relationship_review import RelationshipReviewRevision

router = APIRouter(
    prefix="/relationship-reviews",
    tags=["relationship-reviews"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/assertions")
async def captured_relationship_assertions(
    report_id: UUID,
    version_number: Annotated[int, Query(ge=1, le=2_147_483_647)],
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> RelationshipAssertionsOut:
    values, unavailable, review_ids = await container.report_relationships(session).assertions(
        claims, report_id, version_number
    )
    response.headers["Cache-Control"] = "no-store"
    return RelationshipAssertionsOut(
        items=list(values), unavailable_labels=list(unavailable), review_ids=review_ids
    )


@router.get("")
async def list_relationship_reviews(
    report_id: UUID,
    version_number: Annotated[int, Query(ge=1, le=2_147_483_647)],
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> RelationshipPageOut:
    values, total = await container.report_relationships(session).list(
        claims, report_id, version_number, limit, offset
    )
    response.headers["Cache-Control"] = "no-store"
    return RelationshipPageOut(items=list(values), total=total, limit=limit, offset=offset)


@router.post("", status_code=201)
async def create_relationship_review(
    body: RelationshipCreateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> RelationshipReviewRevision:
    value = await container.report_relationships(session).create(
        claims, body.report_id, body.version_number, body.to_domain(), context
    )
    response.headers["Cache-Control"] = "no-store"
    return value


@router.get("/{relationship_id}")
@router.get("/{relationship_id}/revisions/{revision_id}")
async def get_relationship_review(
    relationship_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    revision_id: UUID | None = None,
) -> RelationshipDetailOut:
    root, revision = await container.report_relationships(session).get(
        claims, relationship_id, revision_id
    )
    response.headers["Cache-Control"] = "no-store"
    return RelationshipDetailOut(root=root, revision=revision)


@router.patch("/{relationship_id}")
async def update_relationship_review(
    relationship_id: UUID,
    body: RelationshipUpdateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> RelationshipReviewRevision:
    value = await container.report_relationships(session).update(
        claims, relationship_id, body.base_revision_id, body.to_domain(), context
    )
    response.headers["Cache-Control"] = "no-store"
    return value
