"""Produce one report version: direction, selection, quality, drafting, advocacy, usage.

The use case resolves the template, the profile and the scope; this module runs the
pipeline of docs/03 section 9 for one version and accounts for every model call.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import replace
from uuid import uuid4

from ase.application.ports.evidence_urls import EvidenceUrlResolver
from ase.application.ports.feeds import EventStore
from ase.application.ports.llm import LlmGateway, LlmUsageRepository, SecretCipher
from ase.application.ports.research import ResearchCollection
from ase.application.reports.advocacy import advocate, apply_advocacy
from ase.application.reports.challenge import run_challenge
from ase.application.reports.citation_checks import check_generated_report_citations
from ase.application.reports.direction import direct
from ase.application.reports.drafting import Draft, draft_body
from ase.application.reports.production_collection import prepare_collection
from ase.application.reports.production_selection import select_for_job
from ase.application.reports.production_types import Job, ProfileLookup, Totals, usage_entry
from ase.application.reports.progress import Progress, reached
from ase.application.reports.render import render_markdown
from ase.application.reports.resolve_links import resolve_cited_links
from ase.application.reports.reused_evidence import REUSE_NOTICE
from ase.application.reports.selection import Selection
from ase.domain.advocacy import DevilsAdvocacy
from ase.domain.direction import Direction
from ase.domain.evidence import EvidenceItem, quality_of_information
from ase.domain.grading import SourceProfile
from ase.domain.judgement_assessment import build_report_assessment
from ase.domain.llm import LlmRole
from ase.domain.report_records import ReportVersion
from ase.domain.reports import ReportBody, ReportHeader, ReportStatus
from ase.domain.research import ResearchMode
from ase.domain.research_context import build_research_context
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
    ) -> None:
        self._store = store
        self._source_profiles = source_profiles
        self._cipher = cipher
        self._gateway = gateway
        self._usage = usage
        self._url_resolver = url_resolver
        self._research = research
        self._private_store_factory = private_store_factory

    async def produce(
        self,
        job: Job,
        profile_for: ProfileLookup,
        before_persist: Callable[[], Awaitable[None]] | None = None,
        *,
        progress: Progress | None = None,
    ) -> ReportVersion:
        totals = Totals()
        await reached(progress, ResearchStage.PLANNING)
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
        )

        def select(extra_terms: tuple[str, ...] = ()) -> Selection:
            return select_for_job(store, self._source_profiles, job, direction, extra_terms)

        selection = select()
        quality = quality_of_information(selection.items, selection.flagged)
        header = ReportHeader(
            template=job.template.id,
            title=job.title,
            scope=job.scope,
            period_from=job.period_from,
            period_to=job.period_to,
            data_cutoff=max((job.now, *(item.captured_at for item in selection.items))),
            requirements=direction.requirement_ids() if direction else (),
        )
        earlier = (
            job.previous.body.key_judgements
            if job.previous is not None
            else job.followup_judgements
        )

        async def make_draft(selected: Selection) -> Draft:
            await reached(progress, ResearchStage.DRAFTING)
            draft = await draft_body(
                self._gateway,
                job.profile,
                self._cipher.decrypt(job.profile.api_key_encrypted),
                job.template,
                replace(
                    header,
                    data_cutoff=max((job.now, *(item.captured_at for item in selected.items))),
                ),
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
        if query is not None and query.mode is ResearchMode.DETAILED:
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
            quality = quality_of_information(selection.items, selection.flagged)
            header = replace(
                header, data_cutoff=max((job.now, *(item.captured_at for item in selection.items)))
            )
            advocacy = next((row.advocacy for row in challenge.reviews if row.advocacy), None)
        elif job.request.devils_advocacy and body.key_judgements and draft.body is not None:
            await reached(progress, ResearchStage.CHALLENGING)
            body, advocacy = await self._advocate(job, profile_for, body, selection.items, totals)
        evidence = selection.items
        status = self._status(draft)
        if self._url_resolver is not None:
            cited = body.cited_labels() | frozenset(advocacy.evidence if advocacy else ())
            if challenge:
                cited |= challenge.cited_labels()
            evidence = await resolve_cited_links(self._url_resolver, evidence, cited)
        await reached(progress, ResearchStage.VALIDATING)
        assessment = build_report_assessment(body, evidence, totals.findings)
        citation_checks = check_generated_report_citations(body, evidence)
        research_context = build_research_context(evidence) if receipt else None
        markdown = render_markdown(
            header, body, evidence, quality, totals.findings,
            direction=direction, advocacy=advocacy, status=status, assessment=assessment,
            citation_checks=citation_checks, research=receipt, challenge=challenge,
            research_context=research_context,
        )  # fmt: skip
        # Usage adapters flush writes. Keep all outbound model and resolution work
        # ahead of them so SQLite's writer lock is held only for persistence. The
        # caller commits these rows atomically with the resulting report version.
        if before_persist is not None:
            await before_persist()
        await reached(progress, ResearchStage.SAVING)
        for usage in totals.usage:
            await self._usage.add(usage)
        return ReportVersion(
            id=uuid4(),
            report_id=job.report_id or uuid4(),
            number=job.previous.number + 1 if job.previous is not None else 1,
            status=status,
            body=body,
            findings=tuple(totals.findings),
            evidence=evidence,
            quality=quality,
            assessment=assessment,
            markdown=markdown,
            profile_id=job.profile.id,
            model=draft.model or job.profile.model,
            prompt_tokens=totals.prompt_tokens,
            completion_tokens=totals.completion_tokens,
            latency_ms=totals.latency_ms,
            attempts=draft.attempts,
            created_at=job.now,
            period_from=header.period_from,
            period_to=header.period_to,
            data_cutoff=header.data_cutoff,
            direction=direction,
            advocacy=advocacy,
            research=receipt,
            citation_checks=citation_checks,
            challenge=challenge,
            research_context=research_context,
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

    @staticmethod
    def _status(draft: Draft) -> ReportStatus:
        if draft.body is None:
            return ReportStatus.FAILED
        if draft.has_errors:
            return ReportStatus.NEEDS_REVIEW
        return ReportStatus.READY
