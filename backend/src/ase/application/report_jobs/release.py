"""Re-authorise durable job responses at the final release boundary."""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import Any
from uuid import UUID

from ase.application.access import AccessContext, AccessPolicy
from ase.application.ports import UnitOfWork
from ase.application.ports.report_jobs import ReportJobRepository
from ase.application.ports.session import SessionCheck
from ase.application.report_jobs.views import error_message, job_view
from ase.domain.errors import Forbidden, InvalidRequest, NotFound
from ase.domain.report_jobs import ReportJob
from ase.domain.users import User


def can_control(context: AccessContext, job: ReportJob) -> bool:
    try:
        context.require_write(job.owner_id, job.team_id)
    except (Forbidden, NotFound):
        return False
    return True


async def release_job(
    actor: User,
    job: ReportJob,
    *,
    guard: Callable[[], AbstractAsyncContextManager[None]],
    check_job: Callable[[ReportJob], Awaitable[None]],
    uow: UnitOfWork,
    access_policy: AccessPolicy,
    check_session: SessionCheck,
    allow_source_summary: bool = False,
) -> dict[str, Any]:
    async with guard():
        detail = True
        try:
            await check_job(job)
        except InvalidRequest as error:
            if not allow_source_summary or error.code != "report_job_source_disabled":
                raise
            detail = False
        finally:
            await uow.rollback()
        try:
            access = await access_policy.context(actor)
            access.require_read(job.owner_id, job.team_id)
            result = job_view(job, detail=detail, can_control=can_control(access, job))
            if not detail:
                result.update(error=error_message("source_disabled"), can_resume=False)
        finally:
            await uow.rollback()
        # No DB cleanup or other awaited work follows this final original-session check.
        await check_session()
        return result


async def load_job(
    actor: User,
    job_id: UUID,
    repo: ReportJobRepository,
    access_policy: AccessPolicy,
    uow: UnitOfWork,
) -> ReportJob:
    """Read a currently visible job without retaining the read transaction."""
    try:
        access = await access_policy.context(actor)
        job = await repo.get(job_id)
        if job is None:
            raise NotFound()
        access.require_read(job.owner_id, job.team_id)
        return job
    finally:
        await uow.rollback()
