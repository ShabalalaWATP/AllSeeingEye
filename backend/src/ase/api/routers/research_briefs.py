"""Authenticated Research Brief creation, scoped reading and insert-only revisions."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, timedelta
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Path, Query, Response
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.research_brief_models import ResearchBriefRevisionRow
from ase.adapters.persistence.research_briefs import SqlResearchBriefRepository, _decode
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
from ase.application.access import AccessContext
from ase.domain.errors import Conflict, Forbidden, NotFound
from ase.domain.research_brief_values import BriefIdentity, BriefValidationError

router = APIRouter(prefix="/research/briefs", tags=["research-briefs"])


def _invalid(exc: BriefValidationError) -> InvalidQuery:
    # The field is useful to clients; never echo submitted private query content.
    return InvalidQuery(
        "The Research Brief is invalid.", fields={exc.field: "Invalid or unsupported value."}
    )


def _write_teams(access: AccessContext, team_id: UUID | None) -> tuple[UUID, ...]:
    teams = tuple(access.memberships)
    # Administrators may create a brief for an existing team without joining it.
    if access.actor.is_admin and team_id is not None and team_id not in access.memberships:
        return (*teams, team_id)
    return teams


async def _visible_row(
    session: AsyncSession,
    access: AccessContext,
    brief_id: UUID,
    revision: int | None = None,
) -> ResearchBriefRevisionRow:
    statement = select(ResearchBriefRevisionRow).where(
        ResearchBriefRevisionRow.brief_id == brief_id,
        visibility_predicate(
            ResearchBriefRevisionRow.owner_id,
            ResearchBriefRevisionRow.team_id,
            access.visibility,
        ),
    )
    if revision is not None:
        statement = statement.where(ResearchBriefRevisionRow.revision == revision)
    else:
        statement = statement.order_by(ResearchBriefRevisionRow.revision.desc()).limit(1)
    row = await session.scalar(statement.execution_options(populate_existing=True))
    if row is None:
        raise NotFound("Research Brief not found.")
    return row


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
    access = await container.access_policy(session).context(user)
    latest = (
        select(
            ResearchBriefRevisionRow.brief_id,
            func.max(ResearchBriefRevisionRow.revision).label("revision"),
        )
        .where(
            visibility_predicate(
                ResearchBriefRevisionRow.owner_id,
                ResearchBriefRevisionRow.team_id,
                access.visibility,
            )
        )
        .group_by(ResearchBriefRevisionRow.brief_id)
        .subquery()
    )
    rows = await session.scalars(
        select(ResearchBriefRevisionRow)
        .join(
            latest,
            and_(
                ResearchBriefRevisionRow.brief_id == latest.c.brief_id,
                ResearchBriefRevisionRow.revision == latest.c.revision,
            ),
        )
        .order_by(ResearchBriefRevisionRow.revised_at.desc(), ResearchBriefRevisionRow.brief_id)
        .limit(limit)
        .offset(offset)
    )
    result = ResearchBriefPageOut(
        items=[ResearchBriefSummaryOut.from_row(row) for row in rows],
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
    access = await container.access_policy(session).context(user, for_update=True)
    access.require_create(body.team_id)
    now = container.clock.now().astimezone(UTC)
    try:
        identity = BriefIdentity(
            id=uuid4(),
            revision=1,
            owner_id=user.id,
            team_id=body.team_id,
            title=body.title,
            preset_id=body.preset_id,
            preset_version=body.preset_version,
            created_at=now,
            revised_at=now,
        )
        brief = body.to_brief(identity)
        saved = await SqlResearchBriefRepository(session).add_revision(
            brief, actor_id=user.id, authorised_team_ids=_write_teams(access, body.team_id)
        )
    except BriefValidationError as exc:
        raise _invalid(exc) from exc
    result = ResearchBriefOut.from_brief(saved)
    validate_request_expiry(container, claims)
    await session.commit()
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
    access = await container.access_policy(session).context(user)
    result = ResearchBriefOut.from_brief(_decode(await _visible_row(session, access, brief_id)))
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
    access = await container.access_policy(session).context(user)
    await _visible_row(session, access, brief_id)
    rows = await session.scalars(
        select(ResearchBriefRevisionRow)
        .where(
            ResearchBriefRevisionRow.brief_id == brief_id,
            visibility_predicate(
                ResearchBriefRevisionRow.owner_id,
                ResearchBriefRevisionRow.team_id,
                access.visibility,
            ),
        )
        .order_by(ResearchBriefRevisionRow.revision.desc())
        .limit(limit)
        .offset(offset)
    )
    result = ResearchBriefPageOut(
        items=[ResearchBriefSummaryOut.from_row(row) for row in rows],
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
    access = await container.access_policy(session).context(user)
    result = ResearchBriefOut.from_brief(
        _decode(await _visible_row(session, access, brief_id, revision))
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
    access = await container.access_policy(session).context(user, for_update=True)
    row = await _visible_row(session, access, brief_id)
    access.require_write(row.owner_id, row.team_id)
    if row.owner_id != user.id:
        raise Forbidden("Only the Research Brief owner can add a revision.")
    if body.team_id != row.team_id:
        raise InvalidQuery(fields={"team_id": "Research Brief scope cannot change."})
    if body.base_revision != row.revision:
        raise Conflict("The Research Brief has a newer revision.")
    prior = _decode(row)
    now = max(
        container.clock.now().astimezone(UTC),
        prior.identity.revised_at + timedelta(microseconds=1),
    )
    try:
        identity = replace(
            prior.identity,
            revision=prior.identity.revision + 1,
            title=body.title,
            preset_id=body.preset_id,
            preset_version=body.preset_version,
            revised_at=now,
            published=False,
        )
        brief = body.to_brief(identity)
        saved = await SqlResearchBriefRepository(session).add_revision(
            brief, actor_id=user.id, authorised_team_ids=_write_teams(access, body.team_id)
        )
    except BriefValidationError as exc:
        raise _invalid(exc) from exc
    result = ResearchBriefOut.from_brief(saved)
    validate_request_expiry(container, claims)
    await session.commit()
    await validate_request_session(container, claims)
    validate_request_expiry(container, claims)
    response.headers["Cache-Control"] = "private, no-store"
    return result
