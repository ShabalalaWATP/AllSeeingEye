"""Scoped claim annotations, separate from immutable generated report contents."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from ase.api.claim_run import run_claim_generation
from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, SessionDep, get_current_user
from ase.api.schemas_claims import (
    ClaimCreateIn,
    ClaimDetailOut,
    ClaimGenerateIn,
    ClaimPageOut,
    ClaimUpdateIn,
)
from ase.application.reports.generate_claims import ClaimGenerationResult
from ase.domain.claim_revisions import ClaimRevision

router = APIRouter(prefix="/claims", tags=["claims"], dependencies=[Depends(get_current_user)])


@router.get("")
async def list_claims(
    report_id: UUID,
    version_number: Annotated[int, Query(ge=1, le=2_147_483_647)],
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=20)] = 20,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> ClaimPageOut:
    values, total = await container.report_claims(session).list(
        claims, report_id, version_number, limit, offset
    )
    response.headers["Cache-Control"] = "no-store"
    return ClaimPageOut(items=list(values), total=total, limit=limit, offset=offset)


@router.post("", status_code=201)
async def create_claim(
    body: ClaimCreateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> ClaimRevision:
    value = await container.report_claims(session).create(
        claims, body.report_id, body.version_number, body.to_domain(), context
    )
    response.headers["Cache-Control"] = "no-store"
    return value


@router.post("/generate")
async def generate_claims(
    body: ClaimGenerateIn,
    request: Request,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> ClaimGenerationResult:
    result = await run_claim_generation(
        request,
        container.generate_claims(session).execute(
            claims, body.report_id, body.version_number, context
        ),
    )
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("/{claim_id}")
@router.get("/{claim_id}/revisions/{revision_id}")
async def get_claim(
    claim_id: UUID,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    revision_id: UUID | None = None,
) -> ClaimDetailOut:
    root, revision = await container.report_claims(session).get(claims, claim_id, revision_id)
    response.headers["Cache-Control"] = "no-store"
    return ClaimDetailOut(root=root, revision=revision)


@router.patch("/{claim_id}")
async def update_claim(
    claim_id: UUID,
    body: ClaimUpdateIn,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    context: ContextDep,
    response: Response,
) -> ClaimRevision:
    value = await container.report_claims(session).update(
        claims, claim_id, body.base_revision_id, body.to_domain(), context
    )
    response.headers["Cache-Control"] = "no-store"
    return value
