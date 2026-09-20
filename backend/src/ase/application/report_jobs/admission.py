"""Freeze candidates and compare admission identity without admitting or publishing work."""

from collections.abc import Awaitable, Callable
from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

from ase.application.model_routing import RoleProfiles
from ase.application.ports import Clock
from ase.application.report_jobs.admission_payload import initial_payload
from ase.application.report_jobs.controls import request_digest, require_same_request
from ase.application.reports.production_types import Job
from ase.application.reports.request import ReportRequest
from ase.domain.errors import Conflict, InvalidRequest
from ase.domain.report_jobs import ReportJob
from ase.domain.users import User

PrepareJob = Callable[[User, ReportRequest], Awaitable[tuple[Job, RoleProfiles]]]
FreezeJob = Callable[[Job, RoleProfiles], dict[str, Any]]


def require_same_submission(
    existing: ReportJob, digest: str | None, brief_ref: tuple[UUID, int] | None
) -> None:
    """An immutable brief identifies its replay; explicit requests retain digest matching."""
    if (existing.brief_id, existing.brief_revision) != (brief_ref or (None, None)):
        raise Conflict("This request identifier belongs to another Research Brief.")
    if digest is not None:
        require_same_request(existing, digest)
    elif brief_ref is None:
        raise InvalidRequest("A brief replay requires an immutable brief reference.")


async def prepare_candidate(
    actor: User,
    request_id: UUID,
    request: ReportRequest,
    *,
    prepare: PrepareJob,
    freeze: FreezeJob,
    clock: Clock,
) -> ReportJob:
    """Preparation and freezing finish before source or database admission locks."""
    digest = request_digest(request)
    prepared, routing = await prepare(actor, request)
    if prepared.actor.id != actor.id or prepared.request.team_id != request.team_id:
        raise InvalidRequest("The prepared report does not match the requested owner or team.")
    report_id, version_id = uuid4(), uuid4()
    prepared = replace(prepared, report_id=report_id)
    try:
        frozen = freeze(prepared, routing)
    except (ValueError, TypeError, RecursionError):
        raise InvalidRequest(
            "The research inputs could not be saved within supported limits. "
            "Reduce the scope or refresh the inputs."
        ) from None
    payload = initial_payload(request, digest, frozen)
    now = clock.now()
    return ReportJob(
        id=uuid4(),
        request_key=request_id,
        owner_id=actor.id,
        team_id=request.team_id,
        title=prepared.title[:300],
        status="queued",
        stage="queued",
        created_at=now,
        updated_at=now,
        payload=payload,
        report_id=report_id,
        version_id=version_id,
    )
