"""Generate a report: resolve template, profile and scope, produce a version, persist it.

Regeneration produces a further version of an existing report from the same scope, with
the previous key judgements shown to the model so it can say what changed.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import replace
from uuid import UUID

from ase.application.dto import RateLimits, RequestContext
from ase.application.model_routing import ModelRouting, RoleProfiles
from ase.application.ports import Clock, RateLimiter, UnitOfWork
from ase.application.ports.llm import SecretCipher
from ase.application.ports.reports import ReportRepository
from ase.application.reports.authorisation import ReportAuthorisation
from ase.application.reports.job_preparation import ReportJobBuilder
from ase.application.reports.map_origin import ReportMapOrigin
from ase.application.reports.production import Job, Producer
from ase.application.reports.production_checkpoint import ProductionCheckpoints
from ase.application.reports.production_result import ProductionResult
from ase.application.reports.progress import Progress
from ase.application.reports.request import ReportRequest
from ase.application.reports.research_inputs import ParentReference, ReportResearchInputs
from ase.application.reports.save_production import SaveProduction
from ase.application.reports.templates import Template
from ase.domain.errors import (
    EncryptionUnavailable,
    InvalidRequest,
    NotFound,
    RateLimited,
)
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.users import User

__all__ = ["GenerateReportUseCase", "ReportRequest"]


class GenerateReportUseCase:
    def __init__(
        self,
        *,
        producer: Producer,
        builder: ReportJobBuilder,
        routing: ModelRouting,
        cipher: SecretCipher,
        reports: ReportRepository,
        clock: Clock,
        limiter: RateLimiter,
        limits: RateLimits,
        save: SaveProduction,
        uow: UnitOfWork,
        map_origin: ReportMapOrigin,
        authorisation: ReportAuthorisation,
        research_inputs: ReportResearchInputs,
    ) -> None:
        self._producer = producer
        self._builder = builder
        self._routing = routing
        self._cipher = cipher
        self._reports = reports
        self._clock = clock
        self._limiter = limiter
        self._limits = limits
        self._save = save
        self._uow = uow
        self._map_origin = map_origin
        self._authorisation = authorisation
        self._research_inputs = research_inputs

    async def execute(
        self,
        actor: User,
        request: ReportRequest,
        context: RequestContext,
        *,
        progress: Progress | None = None,
    ) -> tuple[ReportRecord, ReportVersion]:
        """A new report from the live evidence: version 1 of a new record."""
        job, routing = await self.prepare_job(actor, request)
        produced = await self._producer.produce_with_claims(
            job,
            routing.profile_for,
            lambda: self._finish_prepared(job),
            progress=progress,
        )
        version = produced.version
        version.model_routing = routing.provenance
        record = ReportRecord(
            id=version.report_id,
            template=job.template.id,
            title=job.title,
            scope=dict(job.scope),
            period_from=job.period_from,
            period_to=job.period_to,
            data_cutoff=version.data_cutoff or job.now,
            status=version.status,
            created_by=actor.id,
            created_at=job.now,
            latest_version=1,
            team_id=request.team_id,
        )
        await self._save.save(
            actor, record, produced, context, creating=True, automation=request.automation
        )
        return record, version

    async def prepare_job(self, actor: User, request: ReportRequest) -> tuple[Job, RoleProfiles]:
        """Authorise and freeze inputs and routing, without generating model output."""
        try:
            template = self._builder.template(request)
            plan = await self._authorisation.prepare(actor, request)
            request = await self._map_origin.resolve(actor, request)
            inputs = await self._research_inputs.prepare(actor, request)
            if inputs.parent is not None:
                request = replace(request, parent_version=inputs.parent.version)
            routing = await self._prepare(actor, request, template, owner_id=actor.id)
            job = inputs.apply(
                await self._builder.build(
                    actor,
                    template,
                    request,
                    routing.required(template.role),
                    self._clock.now(),
                    plan=plan,
                )
            )
            if plan is not None:
                job = replace(
                    job,
                    scope={
                        **job.scope,
                        "collection_plan_revision": {
                            "id": str(plan.id),
                            "updated_at": plan.updated_at.isoformat(),
                        },
                    },
                )
            return job, routing
        finally:
            # Jobs may wait in a queue or perform network calls. Neither keeps this read snapshot.
            await self._uow.rollback()

    async def produce_prepared(
        self,
        job: Job,
        routing: RoleProfiles,
        *,
        checkpoints: ProductionCheckpoints | None = None,
        progress: Progress | None = None,
        before_persist: Callable[[], Awaitable[None]] | None = None,
    ) -> ProductionResult:
        """Produce a frozen job without saving its report; the caller owns the final transaction."""

        async def authorise() -> None:
            await self.revalidate_prepared(job)
            if before_persist is not None:
                await before_persist()

        result = await self._producer.produce_with_claims(
            job,
            routing.profile_for,
            authorise,
            progress=progress,
            checkpoints=checkpoints,
        )
        result.version.model_routing = routing.provenance
        return result

    async def revalidate_prepared(self, job: Job) -> None:
        """Recheck frozen references and release guards before another job session is used."""
        try:
            await self._finish_prepared(job)
        finally:
            await self._uow.rollback()

    async def _finish_prepared(self, job: Job) -> None:
        if job.request.parent_report_id is not None and job.request.parent_version is None:
            raise InvalidRequest("Prepared research must reference an exact parent version.")
        plan = await self._authorisation.prepare(job.actor, job.request)
        if plan is not None and job.scope.get("collection_plan_revision") != {
            "id": str(plan.id),
            "updated_at": plan.updated_at.isoformat(),
        }:
            raise InvalidRequest("The collection plan changed after research was prepared.")
        parent = (
            ParentReference(job.request.parent_report_id, job.request.parent_version, job.actor.id)
            if job.request.parent_report_id is not None and job.request.parent_version is not None
            else None
        )
        if parent is None and job.subscription_baseline is not None:
            parent = ParentReference(
                job.subscription_baseline.report_id, job.subscription_baseline.number, job.actor.id
            )
        await self._authorisation.finish(job.actor, job.request, None, plan, parent)

    async def regenerate(
        self,
        actor: User,
        report_id: UUID,
        context: RequestContext,
        *,
        progress: Progress | None = None,
    ) -> tuple[ReportRecord, ReportVersion]:
        """A further version of an existing report, judged against its previous judgements."""
        record = await self._reports.get(report_id)
        if record is None:
            raise NotFound()
        request = replace(
            ReportRequest.from_scope(record.template, record.scope), team_id=record.team_id
        )
        plan = await self._authorisation.prepare(actor, request, record)
        request = await self._map_origin.resolve(actor, request, owner_id=record.created_by)
        previous = await self._reports.get_version(report_id, record.latest_version)
        if previous is None:
            raise NotFound()
        # The saved edition owns the authored task, independently of later brief edits.
        request = replace(request, canonical_requirements=previous.canonical_requirements)
        inputs = await self._research_inputs.prepare(
            actor, request, previous, owner_id=record.created_by
        )
        template = self._builder.template(request)
        routing = await self._prepare(actor, request, template, owner_id=record.created_by)
        profile = routing.required(template.role)
        now = self._clock.now()
        job = await self._builder.build(
            actor,
            template,
            request,
            profile,
            now,
            previous=previous,
            report_id=record.id,
            plan=plan,
        )
        job = inputs.apply(job)
        await self._uow.rollback()
        produced = await self._producer.produce_with_claims(
            job,
            routing.profile_for,
            lambda: self._authorisation.finish(actor, request, record, plan, inputs.parent),
            progress=progress,
        )
        version = produced.version
        version.model_routing = routing.provenance
        record.status = version.status
        record.latest_version = version.number
        record.period_from = job.period_from
        record.period_to = job.period_to
        record.data_cutoff = version.data_cutoff or now
        await self._save.save(
            actor, record, produced, context, creating=False, automation=request.automation
        )
        return record, version

    async def _prepare(
        self, actor: User, request: ReportRequest, template: Template, *, owner_id: UUID
    ) -> RoleProfiles:
        retry_after = self._limiter.hit(
            f"reports:{actor.id}", self._limits.reports_per_user, self._limits.hourly_window_seconds
        )
        if retry_after is not None:
            raise RateLimited(retry_after)
        routing = await self._routing.snapshot(
            team_id=request.team_id,
            personal_owner_id=owner_id,
            profile_id=request.profile_id,
            role=template.role,
        )
        if not self._cipher.available:
            raise EncryptionUnavailable()
        return routing
