"""Generate a report: resolve template, profile and scope, produce a version, persist it.

Regeneration produces a further version of an existing report from the same scope, with
the previous key judgements shown to the model so it can say what changed.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.ai_usage import AiUsageAccounting
from ase.application.auditing import Auditor
from ase.application.dto import RateLimits, RequestContext
from ase.application.model_routing import ModelRouting, RoleProfiles
from ase.application.ports import Clock, RateLimiter, UnitOfWork
from ase.application.ports.claims import ClaimRepository
from ase.application.ports.direction import AoiRepository, PlanRepository
from ase.application.ports.evidence_urls import EvidenceUrlResolver
from ase.application.ports.feeds import EventStore
from ase.application.ports.geo import CountryDirectory
from ase.application.ports.llm import (
    LlmBindingRepository,
    LlmGateway,
    LlmProfileRepository,
    LlmUsageRepository,
    SecretCipher,
)
from ase.application.ports.map_views import MapViewRepository
from ase.application.ports.report_export import AsyncReportProjector
from ase.application.ports.reports import ReportRepository
from ase.application.ports.research import ResearchCollection
from ase.application.ports.research_inputs import ResearchInputStore
from ase.application.ports.trackers import ConflictDirectory
from ase.application.reports.authorisation import ReportAuthorisation
from ase.application.reports.automatic_claims import AutomaticClaims
from ase.application.reports.fresh_web_research import FreshWebResearch
from ase.application.reports.job_preparation import ReportJobBuilder
from ase.application.reports.map_origin import ReportMapOrigin
from ase.application.reports.original_followthrough import OriginalFollowThrough
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
from ase.domain.grading import SourceProfile
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.users import User

__all__ = ["GenerateReportUseCase", "ReportRequest"]


class GenerateReportUseCase:
    def __init__(
        self,
        *,
        store: EventStore,
        source_profiles: Mapping[str, SourceProfile],
        countries: CountryDirectory,
        conflicts: ConflictDirectory,
        plans: PlanRepository,
        aois: AoiRepository,
        llm_profiles: LlmProfileRepository,
        usage: LlmUsageRepository,
        cipher: SecretCipher,
        gateway: LlmGateway,
        reports: ReportRepository,
        clock: Clock,
        limiter: RateLimiter,
        limits: RateLimits,
        auditor: Auditor,
        uow: UnitOfWork,
        access: AccessPolicy,
        backgrounds: Mapping[str, Callable[[], Awaitable[str]]] | None = None,
        url_resolver: EvidenceUrlResolver | None = None,
        research: ResearchCollection | None = None,
        private_store_factory: Callable[[], EventStore] | None = None,
        research_inputs: ResearchInputStore | None = None,
        llm_bindings: LlmBindingRepository | None = None,
        map_views: MapViewRepository | None = None,
        claims: ClaimRepository | None = None,
        web_research: FreshWebResearch | None = None,
        original_followthrough: OriginalFollowThrough | None = None,
        projector: AsyncReportProjector | None = None,
        ai_usage: AiUsageAccounting | None = None,
    ) -> None:
        self._backgrounds = dict(backgrounds or {})
        self._producer = Producer(
            store=store,
            source_profiles=source_profiles,
            cipher=cipher,
            gateway=gateway,
            usage=usage,
            url_resolver=url_resolver,
            research=research,
            web_research=web_research,
            original_followthrough=original_followthrough,
            private_store_factory=private_store_factory,
            automatic_claims=AutomaticClaims(gateway, cipher, clock, limiter)
            if claims is not None
            else None,
            projector=projector,
            ai_usage=ai_usage,
        )
        self._builder = ReportJobBuilder(countries, conflicts, aois, self._backgrounds)
        self._plans = plans
        self._routing = ModelRouting(llm_profiles, llm_bindings)
        self._cipher = cipher
        self._reports = reports
        self._clock = clock
        self._limiter = limiter
        self._limits = limits
        self._save = SaveProduction(reports, claims, access, auditor, uow)
        self._uow = uow
        self._map_origin = ReportMapOrigin(access, reports, map_views)
        self._authorisation = ReportAuthorisation(
            access, reports, plans, aois, uow, self._map_origin
        )
        self._research_inputs = ReportResearchInputs(access, reports, research_inputs)

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
