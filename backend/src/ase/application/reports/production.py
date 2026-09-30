"""Produce one report version: direction, selection, quality, drafting, advocacy, usage.

The use case resolves the template, the profile and the scope; this module runs the
pipeline of docs/03 section 9 for one version and accounts for every model call.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from functools import partial

from ase.application.ai_usage import AiUsageAccounting
from ase.application.ai_usage_gateway import AllowanceLlmGateway
from ase.application.ports.evidence_urls import EvidenceUrlResolver
from ase.application.ports.feeds import EventStore
from ase.application.ports.llm import LlmGateway, LlmUsageRepository, SecretCipher
from ase.application.ports.report_export import AsyncReportProjector
from ase.application.ports.research import (
    ResearchCollection,
)
from ase.application.reports.area_context import AreaContextService, attach_area_context
from ase.application.reports.automatic_claims import AutomaticClaims
from ase.application.reports.evidence_rerank import EvidenceReranker
from ase.application.reports.fresh_web_research import FreshWebResearch
from ase.application.reports.original_followthrough import OriginalFollowThrough
from ase.application.reports.production_analysis import analyse_body
from ase.application.reports.production_checkpoint import (
    ProductionCheckpoints,
)
from ase.application.reports.production_completion import complete_production
from ase.application.reports.production_drafting import draft_for_job
from ase.application.reports.production_model_roles import (
    entail_for_job,
    explain_for_job,
)
from ase.application.reports.production_preparation import prepare_production
from ase.application.reports.production_result import ProductionResult
from ase.application.reports.production_review import review_for_job
from ase.application.reports.production_types import Job, ProfileLookup
from ase.application.reports.production_version import build_version
from ase.application.reports.progress import Progress
from ase.domain.ai_usage import AiAttribution
from ase.domain.grading import SourceProfile
from ase.domain.report_records import ReportVersion

__all__ = ["Job", "Producer"]


class Producer:
    def __init__(
        self,
        *,
        store: EventStore,
        source_profiles: Mapping[str, SourceProfile],
        cipher: SecretCipher,
        gateway: LlmGateway,
        usage: LlmUsageRepository,
        url_resolver: EvidenceUrlResolver | None = None,
        research: ResearchCollection | None = None,
        private_store_factory: Callable[[], EventStore] | None = None,
        automatic_claims: AutomaticClaims | None = None,
        web_research: FreshWebResearch | None = None,
        original_followthrough: OriginalFollowThrough | None = None,
        projector: AsyncReportProjector | None = None,
        ai_usage: AiUsageAccounting | None = None,
        reranker: EvidenceReranker | None = None,
        area_context: AreaContextService | None = None,
    ) -> None:
        self._store = store
        self._source_profiles = source_profiles
        self._cipher = cipher
        self._gateway = gateway
        self._usage = usage
        self._url_resolver = url_resolver
        self._research = research
        self._private_store_factory = private_store_factory
        self._automatic_claims = automatic_claims
        self._web_research = web_research
        self._original_followthrough = original_followthrough
        self._projector = projector
        self._ai_usage = ai_usage
        self._reranker = reranker
        self._area_context = area_context

    async def produce(
        self,
        job: Job,
        profile_for: ProfileLookup,
        before_persist: Callable[[], Awaitable[None]] | None = None,
        *,
        progress: Progress | None = None,
        checkpoints: ProductionCheckpoints | None = None,
    ) -> ReportVersion:
        result = await self.produce_with_claims(
            job, profile_for, before_persist, progress=progress, checkpoints=checkpoints
        )
        return result.version

    def _metered_gateway(self, job: Job) -> LlmGateway:
        """Every model call in the job counts against the owner's AI allowance when metered."""
        if self._ai_usage is None:
            return self._gateway
        return AllowanceLlmGateway(
            self._gateway,
            self._ai_usage,
            attribution=AiAttribution.actor(job.actor.id, job.request.team_id),
            profile_id=None,
            purpose_prefix="report",
        )

    async def produce_with_claims(
        self,
        job: Job,
        profile_for: ProfileLookup,
        before_persist: Callable[[], Awaitable[None]] | None = None,
        *,
        progress: Progress | None = None,
        checkpoints: ProductionCheckpoints | None = None,
    ) -> ProductionResult:
        gateway = self._metered_gateway(job)
        prepared = await prepare_production(
            job,
            profile_for,
            checkpoints=checkpoints,
            gateway=gateway,
            cipher=self._cipher,
            research=self._research,
            private_store_factory=self._private_store_factory,
            shared_store=self._store,
            web_research=self._web_research,
            reranker=self._reranker,
            source_profiles=self._source_profiles,
            original_followthrough=self._original_followthrough,
            area_context=self._area_context,
            progress=progress,
        )
        totals, direction = prepared.totals, prepared.direction
        receipt, query, selection = prepared.receipt, prepared.query, prepared.selection
        make_draft = partial(
            draft_for_job,
            job=job,
            gateway=gateway,
            cipher=self._cipher,
            direction=direction,
            receipt=receipt,
            original_context=prepared.original_context,
            totals=totals,
            checkpoints=checkpoints,
            progress=progress,
        )
        first_selection = selection
        draft = await make_draft(selection)
        draft, selection, body, advocacy, challenge = await review_for_job(
            job,
            draft,
            selection,
            query=query,
            snapshot=prepared.snapshot,
            source_operations=prepared.source_operations,
            checkpoints=checkpoints,
            collection=self._research,
            profiles=self._source_profiles,
            store=prepared.store,
            gateway=gateway,
            cipher=self._cipher,
            profile_for=profile_for,
            totals=totals,
            select=prepared.select,
            redraft=make_draft,
            progress=progress,
        )
        # A challenge can change what the reader will see, so the containment split,
        # which is a statement about exactly that evidence, is computed again.
        receipt = await attach_area_context(
            self._area_context, job, query, selection, receipt, self._store, first_selection
        )
        body = await analyse_body(
            job, gateway, self._cipher, body, selection, direction, totals, checkpoints
        )
        # The reviews read the finished text, so they run after the analysis pass.
        # A failed draft has no judgements, so these passes return without a model call.
        review = (job, profile_for, body, selection.items, totals, gateway, self._cipher)
        await entail_for_job(*review)
        await explain_for_job(*review)
        version = await build_version(
            job,
            draft,
            body,
            selection,
            totals,
            direction=direction,
            receipt=receipt,
            advocacy=advocacy,
            challenge=challenge,
            url_resolver=self._url_resolver,
            progress=progress,
            projector=self._projector,
        )
        return await complete_production(
            version,
            job,
            totals,
            self._automatic_claims,
            profile_for,
            before_persist,
            progress,
            self._usage,
            gateway=gateway if self._ai_usage is not None else None,
        )
