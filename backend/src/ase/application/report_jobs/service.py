"""Authorised admission, inspection and explicit controls for durable report work."""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager, nullcontext
from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.dto import RequestContext
from ase.application.model_routing import RoleProfiles
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.report_jobs import ReportJobRepository
from ase.application.report_jobs.controls import (
    request_digest,
    require_capacity,
    require_same_request,
    resumed_payload,
)
from ase.application.report_jobs.views import error_message, job_view, refresh_summary
from ase.application.reports.production_types import Job
from ase.application.reports.request import ReportRequest
from ase.domain.errors import Conflict, Forbidden, InvalidRequest, NotFound
from ase.domain.report_jobs import ReportJob
from ase.domain.users import User

SessionCheck = Callable[[], Awaitable[None]]
JobCheck = Callable[[ReportJob], Awaitable[None]]
PrepareJob = Callable[[User, ReportRequest], Awaitable[tuple[Job, RoleProfiles]]]
FreezeJob = Callable[[Job, RoleProfiles], dict[str, Any]]
SourceGuard = Callable[[], AbstractAsyncContextManager[None]]


def _can_control(context: AccessContext, job: ReportJob) -> bool:
    try:
        context.require_write(job.owner_id, job.team_id)
    except (Forbidden, NotFound):
        return False
    return True


class ReportJobService:
    """Callbacks perform DB-only checks and must not reacquire the source guard.

    The source guard precedes administration locks. Preparation and freezing finish
    before admission locks; only the worker may perform paid provider requests.
    """

    def __init__(
        self,
        *,
        repo: ReportJobRepository,
        access: AccessPolicy,
        uow: UnitOfWork,
        clock: Clock,
        prepare_job: PrepareJob,
        freeze: FreezeJob,
        check_job: JobCheck,
        cancel: Callable[[UUID, UUID | None], None],
        source_guard: SourceGuard | None = None,
        check_resume: JobCheck | None = None,
    ) -> None:
        self._repo, self._access, self._uow, self._clock = repo, access, uow, clock
        self._prepare, self._freeze = prepare_job, freeze
        self._check_job, self._strict_check = check_job, check_resume or check_job
        self._cancel = cancel
        self._guard: SourceGuard = source_guard or nullcontext

    async def create(
        self,
        actor: User,
        request_id: UUID,
        request: ReportRequest,
        context: RequestContext,
        *,
        check_session: SessionCheck,
    ) -> dict[str, Any]:
        digest = request_digest(request)
        await check_session()
        try:
            access = await self._access.context(actor)
            access.require_create(request.team_id)
            existing = await self._repo.get_by_request(actor.id, request_id)
            if existing is not None:
                access.require_read(existing.owner_id, existing.team_id)
                require_same_request(existing, digest)
        finally:
            await self._uow.rollback()
        if existing is not None:
            return await self._release(actor, existing, check_session)
        prepared, routing = await self._prepare(actor, request)
        if prepared.actor.id != actor.id or prepared.request.team_id != request.team_id:
            raise InvalidRequest("The prepared report does not match the requested owner or team.")
        report_id, version_id = uuid4(), uuid4()
        prepared = replace(prepared, report_id=report_id)
        try:
            frozen = self._freeze(prepared, routing)
        except (ValueError, TypeError, RecursionError):
            raise InvalidRequest(
                "The research inputs could not be saved within supported limits. "
                "Reduce the scope or refresh the inputs."
            ) from None
        payload = {
            "schema_version": 1,
            "input": frozen,
            "request_digest": digest,
            "sections": {},
            "calls": [],
            "collection": None,
        }
        refresh_summary(payload)
        now = self._clock.now()
        candidate = ReportJob(
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
        async with self._guard():
            try:
                access = await self._access.context(actor, for_update=True)
                access.require_create(candidate.team_id)
                # The lock serialises duplicate admission and quotas across SQLite writers.
                existing = await self._repo.get_by_request(actor.id, request_id)
                if existing is not None:
                    access.require_read(existing.owner_id, existing.team_id)
                    require_same_request(existing, digest)
                    await self._uow.rollback()
                    candidate = existing
                else:
                    await self._strict_check(candidate)
                    await require_capacity(self._repo, actor.id, creating=True)
                    await check_session()
                    await self._repo.add(candidate)
                    await self._uow.commit()
            except BaseException:
                await self._uow.rollback()
                raise
        return await self._release(actor, candidate, check_session)

    async def _load(self, actor: User, job_id: UUID) -> ReportJob:
        try:
            access = await self._access.context(actor)
            job = await self._repo.get(job_id)
            if job is None:
                raise NotFound()
            access.require_read(job.owner_id, job.team_id)
            return job
        finally:
            await self._uow.rollback()

    async def _release(
        self,
        actor: User,
        job: ReportJob,
        check_session: SessionCheck,
        *,
        allow_source_summary: bool = False,
    ) -> dict[str, Any]:
        async with self._guard():
            detail = True
            try:
                await self._check_job(job)
            except InvalidRequest as error:
                if not allow_source_summary or error.code != "report_job_source_disabled":
                    raise
                detail = False
            finally:
                await self._uow.rollback()
            try:
                access = await self._access.context(actor)
                access.require_read(job.owner_id, job.team_id)
                result = job_view(job, detail=detail, can_control=_can_control(access, job))
                if not detail:
                    result.update(error=error_message("source_disabled"), can_resume=False)
            finally:
                await self._uow.rollback()
            # No DB cleanup or other awaited work follows this final original-session check.
            await check_session()
            return result

    async def read(
        self,
        actor: User,
        job_id: UUID,
        *,
        check_session: SessionCheck,
    ) -> dict[str, Any]:
        await check_session()
        return await self._release(actor, await self._load(actor, job_id), check_session)

    async def list(
        self,
        actor: User,
        limit: int,
        *,
        check_session: SessionCheck,
    ) -> list[dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= 50:
            raise InvalidRequest("Choose between one and fifty report jobs.")
        await check_session()
        try:
            access = await self._access.context(actor)
            jobs = await self._repo.list_visible(access.visibility, limit=limit)
        finally:
            await self._uow.rollback()
        async with self._guard():
            for job in jobs:
                # Thin rows contain progress metadata only. The callback must not
                # load frozen evidence or perform a provider request for this list.
                await self._check_job(job)
            try:
                access = await self._access.context(actor)
                result = []
                for job in jobs:
                    try:
                        access.require_read(job.owner_id, job.team_id)
                    except NotFound:
                        continue
                    result.append(
                        job_view(job, detail=False, can_control=_can_control(access, job))
                    )
            finally:
                await self._uow.rollback()
            await check_session()
            return result

    async def pause(
        self,
        actor: User,
        job_id: UUID,
        *,
        check_session: SessionCheck,
    ) -> dict[str, Any]:
        await check_session()
        async with self._guard():
            try:
                access = await self._access.context(actor, for_update=True)
                job = await self._repo.get(job_id)
                if job is None:
                    raise NotFound()
                access.require_write(job.owner_id, job.team_id)
                if job.status in {"completed", "needs_review"}:
                    raise InvalidRequest("A completed report cannot be paused.")
                if job.status in {"queued", "running"}:
                    result = await self._repo.pause(
                        job.id,
                        expected_revision=job.revision,
                        now=self._clock.now(),
                    )
                    if result is None:
                        raise Conflict()
                else:
                    result = job
                await check_session()
                await self._uow.commit()
            except BaseException:
                await self._uow.rollback()
                raise
            # A late pause request must never cancel a newly resumed lease.
            self._cancel(job.id, job.lease_token)
        return await self._release(actor, result, check_session, allow_source_summary=True)

    async def resume(
        self,
        actor: User,
        job_id: UUID,
        *,
        check_session: SessionCheck,
    ) -> dict[str, Any]:
        await check_session()
        async with self._guard():
            try:
                access = await self._access.context(actor, for_update=True)
                job = await self._repo.get(job_id)
                if job is None:
                    raise NotFound()
                access.require_write(job.owner_id, job.team_id)
                if job.status in {"completed", "needs_review"}:
                    raise InvalidRequest("A completed report cannot be resumed.")
                await self._strict_check(job)
                if job.status in {"queued", "running"}:
                    result = job
                else:
                    await require_capacity(self._repo, job.owner_id, creating=False)
                    payload = resumed_payload(job)
                    refresh_summary(payload)
                    resumed = await self._repo.resume(
                        job.id,
                        expected_revision=job.revision,
                        now=self._clock.now(),
                        payload=payload,
                    )
                    if resumed is None:
                        raise Conflict()
                    result = resumed
                await check_session()
                await self._uow.commit()
            except BaseException:
                await self._uow.rollback()
                raise
        return await self._release(actor, result, check_session)

    async def discard(
        self,
        actor: User,
        job_id: UUID,
        *,
        check_session: SessionCheck,
    ) -> None:
        """Discard progress only. Finished reports remain in their existing repository."""
        await check_session()
        try:
            access = await self._access.context(actor, for_update=True)
            job = await self._repo.get(job_id)
            if job is None:
                raise NotFound()
            access.require_write(job.owner_id, job.team_id)
            if job.status in {"queued", "running"}:
                raise InvalidRequest("Pause this report job before discarding its progress.")
            await check_session()
            if not await self._repo.discard(job.id, expected_revision=job.revision):
                raise Conflict()
            await self._uow.commit()
        except BaseException:
            await self._uow.rollback()
            raise
        await check_session()
