"""Start, inspect and control authorised durable report work."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.adapters.persistence.research_briefs import _decode
from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.routers.research_briefs import _invalid, _visible_row
from ase.api.schemas_report_jobs import (
    BriefJobCreateIn,
    ReportJobCreateIn,
    ReportJobOut,
    ReportJobsOut,
    public_job,
)
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.application.research.brief_conversion import run_request_from_brief
from ase.domain.research_brief_values import BriefValidationError

router = APIRouter(prefix="/report-jobs", tags=["report-jobs"])


@router.delete("/{job_id}", status_code=204)
async def discard_job(
    job_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
) -> Response:
    await container.report_jobs(session).discard(
        user,
        job_id,
        check_session=lambda: validate_request_session(container, claims, session=session),
    )
    validate_request_expiry(container, claims)
    return Response(status_code=204, headers={"Cache-Control": "private, no-store"})


@router.post("", status_code=202)
async def create_job(
    body: ReportJobCreateIn,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> ReportJobOut:
    result = await container.report_jobs(session).create(
        user,
        body.request_id,
        body.report.to_request(),
        context,
        check_session=lambda: validate_request_session(container, claims, session=session),
    )
    response.headers["Cache-Control"] = "private, no-store"
    payload = public_job(result)
    validate_request_expiry(container, claims)
    return payload


@router.post("/from-brief", status_code=202)
async def create_job_from_brief(
    body: BriefJobCreateIn,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    context: ContextDep,
    response: Response,
) -> ReportJobOut:
    """Pin the exact immutable brief revision before report-job preparation."""
    access = await container.access_policy(session).context(user)
    brief = _decode(await _visible_row(session, access, body.brief_id, body.revision))
    access.require_same_scope(
        user.id, brief.identity.team_id, brief.identity.owner_id, brief.identity.team_id
    )
    access.require_create(brief.identity.team_id)
    try:
        request = run_request_from_brief(brief, now=container.clock.now())
    except BriefValidationError as exc:
        raise _invalid(exc) from exc
    result = await container.report_jobs(session).create(
        user,
        body.request_id,
        request,
        context,
        check_session=lambda: validate_request_session(container, claims, session=session),
        brief_ref=(body.brief_id, body.revision),
    )
    response.headers["Cache-Control"] = "private, no-store"
    payload = public_job(result)
    validate_request_expiry(container, claims)
    return payload


@router.get("")
async def list_jobs(
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ReportJobsOut:
    values = await container.report_jobs(session).list(
        user,
        limit,
        check_session=lambda: validate_request_session(container, claims, session=session),
    )
    response.headers["Cache-Control"] = "private, no-store"
    payload = ReportJobsOut(items=[public_job(value) for value in values])
    validate_request_expiry(container, claims)
    return payload


@router.get("/{job_id}")
async def get_job(
    job_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> ReportJobOut:
    result = await container.report_jobs(session).read(
        user,
        job_id,
        check_session=lambda: validate_request_session(container, claims, session=session),
    )
    response.headers["Cache-Control"] = "private, no-store"
    payload = public_job(result)
    validate_request_expiry(container, claims)
    return payload


@router.post("/{job_id}/pause")
async def pause_job(
    job_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> ReportJobOut:
    result = await container.report_jobs(session).pause(
        user,
        job_id,
        check_session=lambda: validate_request_session(container, claims, session=session),
    )
    response.headers["Cache-Control"] = "private, no-store"
    payload = public_job(result)
    validate_request_expiry(container, claims)
    return payload


@router.post("/{job_id}/resume", status_code=202)
async def resume_job(
    job_id: UUID,
    user: CurrentUser,
    claims: ClaimsDep,
    session: SessionDep,
    container: ContainerDep,
    response: Response,
) -> ReportJobOut:
    result = await container.report_jobs(session).resume(
        user,
        job_id,
        check_session=lambda: validate_request_session(container, claims, session=session),
    )
    response.headers["Cache-Control"] = "private, no-store"
    payload = public_job(result)
    validate_request_expiry(container, claims)
    return payload
