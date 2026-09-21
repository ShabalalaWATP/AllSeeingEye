"""Authorised admission, inspection and explicit controls for durable report work."""

from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager, nullcontext
from dataclasses import replace
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.dto import RequestContext
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.report_jobs import ReportJobRepository
from ase.application.report_jobs.admission import (
    FreezeJob,
    PrepareJob,
    prepare_candidate,
    require_same_submission,
)
from ase.application.report_jobs.controls import (
    request_digest,
    require_capacity,
    require_discardable,
    resumed_payload,
)
from ase.application.report_jobs.release import can_control, load_job, release_job
from ase.application.report_jobs.views import job_view, refresh_summary
from ase.application.reports.request import ReportRequest
from ase.application.research.brief_conversion import run_request_from_brief
from ase.domain.errors import Conflict, InvalidRequest, NotFound
from ase.domain.report_jobs import ReportJob
from ase.domain.research_brief import ResearchBrief
from ase.domain.users import User

__all__ = ["FreezeJob", "PrepareJob", "ReportJobService"]

SessionCheck = Callable[[], Awaitable[None]]
JobCheck = Callable[[ReportJob], Awaitable[None]]
SourceGuard = Callable[[], AbstractAsyncContextManager[None]]
EditionAction = Literal["pause", "resume", "discard"]
EditionControl = Callable[[UUID, EditionAction, datetime], Awaitable[None]]
MonthlyCheck = Callable[[UUID, UUID | None, datetime], Awaitable[None]]


class ReportJobService:
    """Callbacks perform DB-only checks and must not reacquire the source guard.

    Source guards precede administration locks; preparation/freezing precede admission.
    Only the worker may perform paid provider requests.
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
        edition_control: EditionControl | None = None,
        check_monthly: MonthlyCheck | None = None,
        admit_research: Callable[[UUID, datetime], Awaitable[None]] | None = None,
    ) -> None:
        self._repo, self._access, self._uow, self._clock = repo, access, uow, clock
        self._prepare, self._freeze = prepare_job, freeze
        self._check_job, self._strict_check = check_job, check_resume or check_job
        self._cancel = cancel
        self._guard: SourceGuard = source_guard or nullcontext
        self._edition_control = edition_control
        self._check_monthly = check_monthly
        self._admit_research = admit_research

    async def create(
        self,
        actor: User,
        request_id: UUID,
        request: ReportRequest | ResearchBrief,
        context: RequestContext,
        *,
        check_session: SessionCheck,
        brief_ref: tuple[UUID, int] | None = None,
    ) -> dict[str, Any]:
        brief = request if isinstance(request, ResearchBrief) else None
        if brief is not None:
            expected_ref = (brief.identity.id, brief.identity.revision)
            if brief_ref is not None and brief_ref != expected_ref:
                raise InvalidRequest("The immutable brief reference does not match.")
            brief_ref = expected_ref
        digest = request_digest(request) if isinstance(request, ReportRequest) else None
        team_id = (
            request.team_id if isinstance(request, ReportRequest) else request.identity.team_id
        )
        await check_session()
        try:
            access = await self._access.context(actor)
            access.require_create(team_id)
            if brief is not None:
                access.require_same_scope(actor.id, team_id, brief.identity.owner_id, team_id)
            existing = await self._repo.get_by_request(actor.id, request_id)
            if existing is not None:
                access.require_read(existing.owner_id, existing.team_id)
                require_same_submission(existing, digest, brief_ref)
        finally:
            await self._uow.rollback()
        if existing is not None:
            return await self._release(actor, existing, check_session)
        resolved = (
            run_request_from_brief(request, now=self._clock.now())
            if isinstance(request, ResearchBrief)
            else request
        )
        candidate = await self.prepare_candidate(actor, request_id, resolved)
        if brief_ref is not None:
            candidate = replace(candidate, brief_id=brief_ref[0], brief_revision=brief_ref[1])
        async with self._guard():
            try:
                candidate = await self.admit_prepared(
                    actor, candidate, check_session=check_session, replay_brief=brief is not None
                )
                await self._uow.commit()
            except BaseException:
                await self._uow.rollback()
                raise
        return await self._release(actor, candidate, check_session)

    async def prepare_candidate(
        self, actor: User, request_id: UUID, request: ReportRequest
    ) -> ReportJob:
        """Freeze without persistence or paid calls, outside source and admission locks."""
        return await prepare_candidate(
            actor,
            request_id,
            request,
            prepare=self._prepare,
            freeze=self._freeze,
            clock=self._clock,
        )

    async def admit_prepared(
        self,
        actor: User,
        candidate: ReportJob,
        *,
        check_session: SessionCheck,
        subscription_id: UUID | None = None,
        replay_brief: bool = False,
    ) -> ReportJob:
        """Admit inside a caller-owned transaction, without commit or rollback.
        The caller holds the source guard and commits the edition link and job together.
        One-off admission uses the same seam inside its own guard and transaction.
        """
        if candidate.owner_id != actor.id:
            raise InvalidRequest("The prepared report owner changed.")
        access = await self._access.context(actor, for_update=True)
        access.require_create(candidate.team_id)
        # The lock serialises duplicate admission and quotas across SQLite writers.
        existing = await self._repo.get_by_request(actor.id, candidate.request_key)
        if existing is not None:
            access.require_read(existing.owner_id, existing.team_id)
            require_same_submission(
                existing,
                None if replay_brief else candidate.payload["request_digest"],
                (candidate.brief_id, candidate.brief_revision)
                if candidate.brief_id is not None and candidate.brief_revision is not None
                else None,
            )
            return existing
        await self._strict_check(candidate)
        await require_capacity(self._repo, actor.id, creating=True)
        if self._check_monthly is not None:
            await self._check_monthly(actor.id, subscription_id, self._clock.now())
        await check_session()
        if self._admit_research is not None:
            await self._admit_research(actor.id, self._clock.now())
        await self._repo.add(candidate)
        return candidate

    async def _load(self, actor: User, job_id: UUID) -> ReportJob:
        return await load_job(actor, job_id, self._repo, self._access, self._uow)

    async def _release(
        self,
        actor: User,
        job: ReportJob,
        check_session: SessionCheck,
        *,
        allow_source_summary: bool = False,
    ) -> dict[str, Any]:
        return await release_job(
            actor,
            job,
            guard=self._guard,
            check_job=self._check_job,
            uow=self._uow,
            access_policy=self._access,
            check_session=check_session,
            allow_source_summary=allow_source_summary,
        )

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
                    result.append(job_view(job, detail=False, can_control=can_control(access, job)))
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
                if self._edition_control is not None:
                    await self._edition_control(job.id, "pause", self._clock.now())
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
                if self._edition_control is not None:
                    await self._edition_control(job.id, "resume", self._clock.now())
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
            require_discardable(job, self._clock.now())
            if self._edition_control is not None:
                await self._edition_control(job.id, "discard", self._clock.now())
            await check_session()
            if not await self._repo.discard(job.id, expected_revision=job.revision):
                raise Conflict()
            await self._uow.commit()
        except BaseException:
            await self._uow.rollback()
            raise
        await check_session()
