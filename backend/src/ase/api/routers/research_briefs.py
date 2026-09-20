"""Authenticated Research Brief creation, scoped reading and insert-only revisions."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser, SessionDep
from ase.api.errors import InvalidQuery
from ase.api.schemas_research_briefs import (
    ResearchBriefDraftIn,
    ResearchBriefOut,
    ResearchBriefPageOut,
    ResearchBriefRevisionIn,
    ResearchBriefSummaryOut,
)
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.application.research.manage_briefs import BriefScopeChange
from ase.domain.research_brief_values import BriefValidationError

router = APIRouter(prefix="/research/briefs", tags=["research-briefs"])


def _invalid(exc: BriefValidationError) -> InvalidQuery:
    # The field is useful to clients; never echo submitted private query content.
    return InvalidQuery(
        "The Research Brief is invalid.", fields={exc.field: "Invalid or unsupported value."}
    )


@router.get("")
async def list_briefs(
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> ResearchBriefPageOut:
    rows = await container.research_briefs(session).list(user, limit, offset)
    result = ResearchBriefPageOut(
        items=[ResearchBriefSummaryOut.from_summary(row) for row in rows],
        limit=limit,
        offset=offset,
    )
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.post("", status_code=201)
async def create_brief(
    body: ResearchBriefDraftIn,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> ResearchBriefOut:
    await validate_request_session(container, claims)
    service = container.research_briefs(session)
    try:
        saved = await service.create(user, body)
    except BriefValidationError as exc:
        raise _invalid(exc) from exc
    result = ResearchBriefOut.from_brief(saved)
    validate_request_expiry(container, claims)
    await service.commit()
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.get("/{brief_id}")
async def get_brief(
    brief_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> ResearchBriefOut:
    result = ResearchBriefOut.from_brief(
        await container.research_briefs(session).get(user, brief_id)
    )
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.get("/{brief_id}/revisions")
async def list_brief_revisions(
    brief_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
) -> ResearchBriefPageOut:
    rows = await container.research_briefs(session).list(user, limit, offset, brief_id)
    result = ResearchBriefPageOut(
        items=[ResearchBriefSummaryOut.from_summary(row) for row in rows],
        limit=limit,
        offset=offset,
    )
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.get("/{brief_id}/revisions/{revision}")
async def get_brief_revision(
    brief_id: UUID,
    revision: Annotated[int, Path(ge=1)],
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> ResearchBriefOut:
    result = ResearchBriefOut.from_brief(
        await container.research_briefs(session).get(user, brief_id, revision)
    )
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result


@router.post("/{brief_id}/revisions", status_code=201)
async def revise_brief(
    brief_id: UUID,
    body: ResearchBriefRevisionIn,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> ResearchBriefOut:
    await validate_request_session(container, claims)
    service = container.research_briefs(session)
    try:
        saved = await service.revise(user, brief_id, body.base_revision, body)
    except BriefScopeChange as exc:
        raise InvalidQuery(fields={"team_id": "Research Brief scope cannot change."}) from exc
    except BriefValidationError as exc:
        raise _invalid(exc) from exc
    result = ResearchBriefOut.from_brief(saved)
    validate_request_expiry(container, claims)
    await service.commit()
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result
