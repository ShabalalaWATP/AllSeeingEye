"""Produce one report version: direction, selection, quality, drafting, advocacy, usage.

The use case resolves the template, the profile and the scope; this module runs the
pipeline of docs/03 section 9 for one version and accounts for every model call.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from functools import partial

from ase.application.ai_usage import AiUsageAccounting
from ase.application.ai_usage_gateway import AllowanceLlmGateway
from ase.application.ports.evidence_urls import EvidenceUrlResolver
from ase.application.ports.feeds import EventStore
from ase.application.ports.llm import LlmGateway, LlmUsageRepository, SecretCipher
from ase.application.ports.report_export import AsyncReportProjector
from ase.application.ports.research import (
    CheckpointedChallengeCollection,
    ResearchCollection,
    SourceOperationCheckpoints,
)
from ase.application.reports.area_context import AreaContextService, attach_area_context
from ase.application.reports.automatic_claims import AutomaticClaims
from ase.application.reports.challenge import run_challenge
from ase.application.reports.challenge_expansion import expand_and_review
from ase.application.reports.drafting import Draft, draft_body
from ase.application.reports.evidence_rerank import EvidenceReranker
from ase.application.reports.fresh_web_research import FreshWebResearch
from ase.application.reports.frozen_challenge import review_frozen
from ase.application.reports.original_followthrough import OriginalFollowThrough
from ase.application.reports.production_checkpoint import (
    ExpansionCheckpoints,
    ProductionCheckpoints,
    ProductionSnapshot,
)
from ase.application.reports.production_collection import prepare_collection
from ase.application.reports.production_completion import complete_production
from ase.application.reports.production_model_roles import advocate_for_job, direct_for_job
from ase.application.reports.production_rerank import rerank_for_job
from ase.application.reports.production_result import ProductionResult
from ase.application.reports.production_selection import select_for_job
from ase.application.reports.production_types import Job, ProfileLookup, Totals, usage_entry
from ase.application.reports.production_version import build_version, header_for
from ase.application.reports.progress import Progress, reached
from ase.application.reports.reused_evidence import REUSE_NOTICE
from ase.application.reports.sections import draft_sections
from ase.application.reports.selection import Selection
from ase.application.reports.subscription_updates import update_guidance
from ase.domain.advocacy import DevilsAdvocacy
from ase.domain.ai_usage import AiAttribution
from ase.domain.evidence import quality_of_information
from ase.domain.grading import SourceProfile
from ase.domain.report_records import ReportVersion
from ase.domain.reports import ReportBody
from ase.domain.research_runs import ResearchStage

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

    async def produce_with_claims(  # noqa: PLR0915 - serial checkpointed report stages
        self,
        job: Job,
        profile_for: ProfileLookup,
        before_persist: Callable[[], Awaitable[None]] | None = None,
        *,
        progress: Progress | None = None,
        checkpoints: ProductionCheckpoints | None = None,
    ) -> ProductionResult:
        gateway = self._metered_gateway(job)
        snapshot = await checkpoints.load_collection() if checkpoints is not None else None
        source_operations = (
            checkpoints
            if isinstance(checkpoints, SourceOperationCheckpoints)
            and checkpoints.source_phase_enabled
            else None
        )
        totals = (
            replace(
                snapshot.totals,
                findings=list(snapshot.totals.findings),
                usage=list(snapshot.totals.usage),
            )
            if snapshot is not None
            else Totals()
        )
        await reached(progress, ResearchStage.PLANNING)
        if snapshot is None:
            direction = await direct_for_job(job, profile_for, totals, gateway, self._cipher)
            store, receipt, query = await prepare_collection(
                job,
                direction,
                totals,
                self._research,
                self._private_store_factory,
                self._store,
                progress,
                gateway=gateway,
                cipher=self._cipher,
                profile_for=profile_for,
                web_research=self._web_research,
                source_operations=source_operations,
            )
        else:
            direction, receipt, query = snapshot.direction, snapshot.receipt, snapshot.query
            store = self._store

        # A resumed job keeps its frozen selection, so no second embedding call is made.
        # Only the unresumed path hands `select` to the challenge, so the challenge's
        # re-selection sees the same similarity map that produced the first selection.
        rerank = await rerank_for_job(
            self._reranker,
            job,
            store,
            direction,
            query,
            receipt,
            totals,
            resumed=snapshot is not None,
        )

        def select(extra_terms: tuple[str, ...] = ()) -> Selection:
            return select_for_job(
                store,
                self._source_profiles,
                job,
                direction,
                extra_terms,
                runtime_query=query,
                receipt=receipt,
                reserve_challenge_slots=source_operations is not None,
                similarity=rerank.similarity,
                rerank_reason=rerank.reason,
            )

        selection = snapshot.selection if snapshot is not None else select()
        original_context = ""
        if receipt is not None and self._original_followthrough is not None:
            if snapshot is None:
                originals = await self._original_followthrough.collect(
                    job, store, selection, receipt
                )
                receipt = replace(receipt, original_followup=originals)
            original_context = await self._original_followthrough.context(receipt.original_followup)
        receipt = await attach_area_context(
            self._area_context, job, query, selection, receipt, self._store
        )
        if checkpoints is not None and snapshot is None:
            snapshot = ProductionSnapshot(
                selection,
                direction,
                receipt,
                query,
                replace(totals, findings=list(totals.findings), usage=list(totals.usage)),
            )
            await checkpoints.save_collection(snapshot)
        earlier = (
            job.previous.body.key_judgements
            if job.previous is not None
            else job.followup_judgements
        )

        async def make_draft(selected: Selection) -> Draft:
            await reached(progress, ResearchStage.DRAFTING)
            draft_fn = (
                draft_body
                if checkpoints is None
                else partial(
                    draft_sections,
                    checkpoints=checkpoints.section_checkpoints,
                )
            )
            draft = await draft_fn(
                gateway,
                job.profile,
                self._cipher.decrypt(job.profile.api_key_encrypted),
                job.template,
                header_for(job, selected, direction),
                job.request.question,
                quality_of_information(selected.items, selected.flagged),
                selected.items,
                earlier,
                direction=direction,
                canonical_requirements=job.request.canonical_requirements,
                background="\n\n".join(
                    filter(
                        None,
                        (
                            job.background,
                            receipt.describe() if receipt else None,
                            original_context,
                            REUSE_NOTICE if job.reused_evidence else None,
                            update_guidance(
                                job.subscription_baseline,
                                selected.items,
                                frozenset(job.request.subscription_seen_signatures),
                                previous_missing=job.request.subscription_previous_report_id
                                is not None
                                and job.subscription_baseline is None,
                            ),
                        ),
                    )
                )
                or None,
            )
            totals.usage.append(
                usage_entry(
                    job, job.profile, f"report:{job.template.id}", draft.body is not None, draft
                )
            )
            totals.add(
                draft.prompt_tokens, draft.completion_tokens, draft.latency_ms, draft.findings
            )
            return draft

        first_selection = selection
        draft = await make_draft(selection)
        body = draft.body or ReportBody()
        advocacy: DevilsAdvocacy | None = None
        challenge = None
        if (
            query is not None
            and query.mode.requires_challenge
            and snapshot is not None
            and source_operations is not None
            and isinstance(checkpoints, ExpansionCheckpoints)
        ):
            outcome = await expand_and_review(
                job,
                draft,
                snapshot,
                collection=self._research
                if isinstance(self._research, CheckpointedChallengeCollection)
                else None,
                source_operations=source_operations,
                checkpoints=checkpoints,
                profiles=self._source_profiles,
                gateway=gateway,
                cipher=self._cipher,
                profile_for=profile_for,
                totals=totals,
                redraft=make_draft,
                progress=progress,
            )
            draft, selection, body, challenge = (
                outcome.draft,
                outcome.selection,
                outcome.body,
                outcome.challenge,
            )
            advocacy = next((row.advocacy for row in challenge.reviews if row.advocacy), None)
        elif query is not None and query.mode.requires_challenge and checkpoints is not None:
            body, challenge = await review_frozen(
                job,
                body,
                selection,
                gateway=gateway,
                cipher=self._cipher,
                profile_for=profile_for,
                totals=totals,
                progress=progress,
            )
            advocacy = next((row.advocacy for row in challenge.reviews if row.advocacy), None)
        elif query is not None and query.mode.requires_challenge:
            original_findings = tuple(draft.findings)
            outcome = await run_challenge(
                job,
                draft,
                selection,
                query=query,
                store=store,
                collection=self._research,
                gateway=gateway,
                cipher=self._cipher,
                profile_for=profile_for,
                totals=totals,
                select=select,
                redraft=make_draft,
                progress=progress,
            )
            if outcome.challenge.redrafted:
                for finding in original_findings:
                    if finding in totals.findings:
                        totals.findings.remove(finding)
            draft, selection, body, challenge = (
                outcome.draft,
                outcome.selection,
                outcome.body,
                outcome.challenge,
            )
            advocacy = next((row.advocacy for row in challenge.reviews if row.advocacy), None)
        elif job.request.devils_advocacy and body.key_judgements and draft.body is not None:
            await reached(progress, ResearchStage.CHALLENGING)
            body, advocacy = await advocate_for_job(
                job, profile_for, body, selection.items, totals, gateway, self._cipher
            )
        # A challenge can change what the reader will see, so the containment split,
        # which is a statement about exactly that evidence, is computed again.
        receipt = await attach_area_context(
            self._area_context, job, query, selection, receipt, self._store, first_selection
        )
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
