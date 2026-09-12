"""Produce one report version: direction, selection, quality, drafting, advocacy, usage.

The use case resolves the template, the profile and the scope; this module runs the
pipeline of docs/03 section 9 for one version and accounts for every model call.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import replace
from functools import partial

from ase.application.ports.evidence_urls import EvidenceUrlResolver
from ase.application.ports.feeds import EventStore
from ase.application.ports.llm import LlmGateway, LlmUsageRepository, SecretCipher
from ase.application.ports.report_export import AsyncReportProjector
from ase.application.ports.research import ResearchCollection
from ase.application.reports.advocacy import advocate, apply_advocacy
from ase.application.reports.automatic_claims import AutomaticClaims
from ase.application.reports.challenge import run_challenge
from ase.application.reports.direction import direct
from ase.application.reports.drafting import Draft, draft_body
from ase.application.reports.fresh_web_research import FreshWebResearch
from ase.application.reports.frozen_challenge import review_frozen
from ase.application.reports.production_checkpoint import ProductionCheckpoints, ProductionSnapshot
from ase.application.reports.production_collection import prepare_collection
from ase.application.reports.production_completion import complete_production
from ase.application.reports.production_result import ProductionResult
from ase.application.reports.production_selection import select_for_job
from ase.application.reports.production_types import Job, ProfileLookup, Totals, usage_entry
from ase.application.reports.production_version import build_version, header_for
from ase.application.reports.progress import Progress, reached
from ase.application.reports.reused_evidence import REUSE_NOTICE
from ase.application.reports.sections import draft_sections
from ase.application.reports.selection import Selection
from ase.domain.advocacy import DevilsAdvocacy
from ase.domain.direction import Direction
from ase.domain.evidence import EvidenceItem, quality_of_information
from ase.domain.grading import SourceProfile
from ase.domain.llm import LlmRole
from ase.domain.report_records import ReportVersion
from ase.domain.reports import ReportBody
from ase.domain.research_runs import ResearchStage
from ase.domain.validation import Finding, Severity

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
        projector: AsyncReportProjector | None = None,
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
        self._projector = projector

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

    async def produce_with_claims(
        self,
        job: Job,
        profile_for: ProfileLookup,
        before_persist: Callable[[], Awaitable[None]] | None = None,
        *,
        progress: Progress | None = None,
        checkpoints: ProductionCheckpoints | None = None,
    ) -> ProductionResult:
        snapshot = await checkpoints.load_collection() if checkpoints is not None else None
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
            direction = await self._direct(job, profile_for, totals)
            store, receipt, query = await prepare_collection(
                job,
                direction,
                totals,
                self._research,
                self._private_store_factory,
                self._store,
                progress,
                gateway=self._gateway,
                cipher=self._cipher,
                profile_for=profile_for,
                web_research=self._web_research,
            )
        else:
            direction, receipt, query = snapshot.direction, snapshot.receipt, snapshot.query
            store = self._store

        def select(extra_terms: tuple[str, ...] = ()) -> Selection:
            return select_for_job(
                store,
                self._source_profiles,
                job,
                direction,
                extra_terms,
                runtime_query=query,
            )

        selection = snapshot.selection if snapshot is not None else select()
        if checkpoints is not None and snapshot is None:
            await checkpoints.save_collection(
                ProductionSnapshot(
                    selection,
                    direction,
                    receipt,
                    query,
                    replace(totals, findings=list(totals.findings), usage=list(totals.usage)),
                )
            )
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
                self._gateway,
                job.profile,
                self._cipher.decrypt(job.profile.api_key_encrypted),
                job.template,
                header_for(job, selected, direction),
                job.request.question,
                quality_of_information(selected.items, selected.flagged),
                selected.items,
                earlier,
                direction=direction,
                background="\n\n".join(
                    filter(
                        None,
                        (
                            job.background,
                            receipt.describe() if receipt else None,
                            REUSE_NOTICE if job.reused_evidence else None,
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

        draft = await make_draft(selection)
        body = draft.body or ReportBody()
        advocacy: DevilsAdvocacy | None = None
        challenge = None
        if query is not None and query.mode.requires_challenge and checkpoints is not None:
            body, challenge = await review_frozen(
                job,
                body,
                selection,
                gateway=self._gateway,
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
                gateway=self._gateway,
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
            body, advocacy = await self._advocate(job, profile_for, body, selection.items, totals)
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
        )

    async def _direct(
        self, job: Job, profile_for: ProfileLookup, totals: Totals
    ) -> Direction | None:
        if job.direction is not None:
            return job.direction
        question = (job.request.question or "").strip()
        if not (job.template.needs_question or job.request.research_mode) or not question:
            return None
        profile = await profile_for(LlmRole.DIRECTION)
        if profile is None:
            totals.findings.append(
                Finding(
                    "direction",
                    Severity.WARNING,
                    "direction",
                    "No enabled model profile plays the direction role; evidence was "
                    "selected without search terms.",
                )
            )
            return None
        key = self._cipher.decrypt(profile.api_key_encrypted)
        draft = await direct(
            self._gateway,
            profile,
            key,
            question,
            job.country_name,
            languages=job.request.research_languages if job.request.research_mode else (),
        )
        purpose = f"report:{job.template.id}:direction"
        totals.usage.append(usage_entry(job, profile, purpose, draft.direction is not None, draft))
        totals.add(draft.prompt_tokens, draft.completion_tokens, draft.latency_ms, draft.findings)
        return draft.direction

    async def _advocate(
        self,
        job: Job,
        profile_for: ProfileLookup,
        body: ReportBody,
        evidence: Sequence[EvidenceItem],
        totals: Totals,
    ) -> tuple[ReportBody, DevilsAdvocacy | None]:
        profile = await profile_for(LlmRole.DEVIL)
        if profile is None:
            totals.findings.append(
                Finding(
                    "advocacy",
                    Severity.WARNING,
                    "devils_advocacy",
                    "No enabled model profile plays the devil role; no contrarian view was taken.",
                )
            )
            return body, None
        key = self._cipher.decrypt(profile.api_key_encrypted)
        draft = await advocate(self._gateway, profile, key, body, evidence)
        purpose = f"report:{job.template.id}:advocacy"
        totals.usage.append(usage_entry(job, profile, purpose, draft.advocacy is not None, draft))
        totals.add(draft.prompt_tokens, draft.completion_tokens, draft.latency_ms, draft.findings)
        if draft.advocacy is None:
            return body, None
        return apply_advocacy(body, draft.advocacy)
