"""Start, inspect and control authorised durable report work."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, ContextDep, CurrentUser, SessionDep
from ase.api.schemas_report_jobs import (
    ReportJobCreateIn,
    ReportJobOut,
    ReportJobsOut,
    public_job,
)
from ase.api.session_guard import validate_request_expiry, validate_request_session

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
        user, job_id, check_session=lambda: validate_request_session(container, claims)
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
        check_session=lambda: validate_request_session(container, claims),
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
        user, limit, check_session=lambda: validate_request_session(container, claims)
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
        user, job_id, check_session=lambda: validate_request_session(container, claims)
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
        check_session=lambda: validate_request_session(container, claims),
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
        check_session=lambda: validate_request_session(container, claims),
    )
    response.headers["Cache-Control"] = "private, no-store"
    payload = public_job(result)
    validate_request_expiry(container, claims)
    return payload
