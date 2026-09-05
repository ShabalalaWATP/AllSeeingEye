"""Produce one report version: direction, selection, quality, drafting, advocacy, usage.

The use case resolves the template, the profile and the scope; this module runs the
pipeline of docs/03 section 9 for one version and accounts for every model call.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from ase.application.ports.feeds import EventStore
from ase.application.ports.llm import LlmGateway, LlmUsageRepository, SecretCipher
from ase.application.reports.advocacy import advocate, apply_advocacy
from ase.application.reports.direction import direct
from ase.application.reports.drafting import Draft, draft_body
from ase.application.reports.render import render_markdown
from ase.application.reports.request import ReportRequest
from ase.application.reports.selection import select_evidence
from ase.application.reports.templates import Template
from ase.domain.advocacy import DevilsAdvocacy
from ase.domain.direction import Direction
from ase.domain.events import BoundingBox
from ase.domain.evidence import EvidenceItem, quality_of_information
from ase.domain.grading import SourceProfile
from ase.domain.llm import LlmProfile, LlmRole, LlmUsage
from ase.domain.report_records import ReportVersion
from ase.domain.reports import ReportBody, ReportHeader, ReportStatus
from ase.domain.trackers import Hazard
from ase.domain.users import User
from ase.domain.validation import Finding, Severity

ProfileLookup = Callable[[LlmRole], Awaitable[LlmProfile | None]]


@dataclass(frozen=True, slots=True)
class Job:
    """Everything one version needs that the use case has already resolved."""

    actor: User
    template: Template
    request: ReportRequest
    profile: LlmProfile
    now: datetime
    window: timedelta
    title: str
    scope: Mapping[str, Any]
    country_name: str | None
    previous: ReportVersion | None = None
    report_id: UUID | None = None
    bbox: BoundingBox | None = None
    countries: tuple[str, ...] = ()
    hazard: Hazard | None = None
    terms: tuple[str, ...] = ()
    background: str | None = None
    direction: Direction | None = None


@dataclass(slots=True)
class Totals:
    """Tokens, latency and findings summed over every model call of one version."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: float = 0.0
    findings: list[Finding] = field(default_factory=list)

    def add(
        self,
        prompt: int | None,
        completion: int | None,
        latency: float,
        findings: Sequence[Finding],
    ) -> None:
        if prompt is not None:
            self.prompt_tokens = (self.prompt_tokens or 0) + prompt
        if completion is not None:
            self.completion_tokens = (self.completion_tokens or 0) + completion
        self.latency_ms += latency
        self.findings.extend(findings)


class Producer:
    def __init__(
        self,
        *,
        store: EventStore,
        source_profiles: Mapping[str, SourceProfile],
        cipher: SecretCipher,
        gateway: LlmGateway,
        usage: LlmUsageRepository,
    ) -> None:
        self._store = store
        self._source_profiles = source_profiles
        self._cipher = cipher
        self._gateway = gateway
        self._usage = usage

    async def produce(self, job: Job, profile_for: ProfileLookup) -> ReportVersion:
        totals = Totals()
        direction = await self._direct(job, profile_for, totals)
        selection = select_evidence(
            self._store,
            self._source_profiles,
            job.template.strategy,
            now=job.now,
            country_iso=job.request.country_iso,
            categories=job.request.categories,
            terms=direction.search_terms if direction else job.terms,
            bbox=job.bbox,
            countries=job.countries,
            hazard=job.hazard,
        )
        quality = quality_of_information(selection.items, selection.flagged)
        header = ReportHeader(
            template=job.template.id,
            title=job.title,
            scope=job.scope,
            period_from=job.now - job.window,
            period_to=job.now,
            data_cutoff=job.now,
            requirements=direction.requirement_ids() if direction else (),
        )
        earlier = job.previous.body.key_judgements if job.previous is not None else ()
        draft = await draft_body(
            self._gateway,
            job.profile,
            self._cipher.decrypt(job.profile.api_key_encrypted),
            job.template,
            header,
            job.request.question,
            quality,
            selection.items,
            earlier,
            direction=direction,
            background=job.background,
        )
        await self._log(
            job, job.profile, f"report:{job.template.id}", draft.body is not None, draft
        )
        totals.add(draft.prompt_tokens, draft.completion_tokens, draft.latency_ms, draft.findings)
        body = draft.body or ReportBody()
        status = self._status(draft)
        advocacy: DevilsAdvocacy | None = None
        if (
            job.request.devils_advocacy
            and body.key_judgements
            and status is not ReportStatus.FAILED
        ):
            body, advocacy = await self._advocate(job, profile_for, body, selection.items, totals)
        markdown = render_markdown(
            header, body, selection.items, quality, totals.findings,
            direction=direction, advocacy=advocacy,
        )  # fmt: skip
        return ReportVersion(
            id=uuid4(),
            report_id=job.report_id or uuid4(),
            number=job.previous.number + 1 if job.previous is not None else 1,
            status=status,
            body=body,
            findings=tuple(totals.findings),
            evidence=selection.items,
            quality=quality,
            markdown=markdown,
            profile_id=job.profile.id,
            model=draft.model or job.profile.model,
            prompt_tokens=totals.prompt_tokens,
            completion_tokens=totals.completion_tokens,
            latency_ms=totals.latency_ms,
            attempts=draft.attempts,
            created_at=job.now,
            direction=direction,
            advocacy=advocacy,
        )

    async def _direct(
        self, job: Job, profile_for: ProfileLookup, totals: Totals
    ) -> Direction | None:
        if job.direction is not None:
            return job.direction
        question = (job.request.question or "").strip()
        if not job.template.needs_question or not question:
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
        draft = await direct(self._gateway, profile, key, question, job.country_name)
        purpose = f"report:{job.template.id}:direction"
        await self._log(job, profile, purpose, draft.direction is not None, draft)
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
        await self._log(job, profile, purpose, draft.advocacy is not None, draft)
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

    async def _log(self, job: Job, profile: LlmProfile, purpose: str, ok: bool, call: Any) -> None:
        """One usage row per model call; the error column carries what went wrong, if anything."""
        findings: Sequence[Finding] = call.findings
        problems = [f.message for f in findings if not ok or f.severity is Severity.ERROR]
        await self._usage.add(
            LlmUsage(
                at=job.now,
                profile_id=profile.id,
                user_id=job.actor.id,
                purpose=purpose,
                ok=ok,
                latency_ms=call.latency_ms,
                prompt_tokens=call.prompt_tokens,
                completion_tokens=call.completion_tokens,
                error="; ".join(problems)[:500] or None,
            )
        )
