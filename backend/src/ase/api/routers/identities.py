"""Scoped operator identity review and exact revision retrieval."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, SessionDep, get_current_user
from ase.api.schemas_identities import (
    IdentityCreateIn,
    IdentityDetailOut,
    IdentityPageOut,
    IdentityUpdateIn,
)
from ase.domain.identity_review import IdentityDecisionRevision

router = APIRouter(
    prefix="/identity-reviews", tags=["identity-reviews"], dependencies=[Depends(get_current_user)]
)


@router.get("")
async def list_identity_reviews(
    report_id: UUID,
    version_number: Annotated[int, Query(ge=1, le=2_147_483_647)],
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> IdentityPageOut:
    values, total = await container.report_identities(session).list(
        claims, report_id, version_number, limit, offset
    )
    response.headers["Cache-Control"] = "no-store"
    return IdentityPageOut(items=list(values), total=total, limit=limit, offset=offset)


@router.post("", status_code=201)
async def create_identity_review(
    body: IdentityCreateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> IdentityDecisionRevision:
    value = await container.report_identities(session).create(
        claims, body.report_id, body.version_number, body.to_domain(), context
    )
    response.headers["Cache-Control"] = "no-store"
    return value


@router.get("/{decision_id}")
@router.get("/{decision_id}/revisions/{revision_id}")
async def get_identity_review(
    decision_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    revision_id: UUID | None = None,
) -> IdentityDetailOut:
    root, revision = await container.report_identities(session).get(
        claims, decision_id, revision_id
    )
    response.headers["Cache-Control"] = "no-store"
    return IdentityDetailOut(root=root, revision=revision)


@router.patch("/{decision_id}")
async def update_identity_review(
    decision_id: UUID,
    body: IdentityUpdateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> IdentityDecisionRevision:
    value = await container.report_identities(session).update(
        claims, decision_id, body.base_revision_id, body.to_domain(), context
    )
    response.headers["Cache-Control"] = "no-store"
    return value
