"""Inputs and in-memory accounting shared by report production stages."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from ase.application.reports.request import ReportRequest
from ase.application.reports.templates import Template
from ase.domain.direction import Direction
from ase.domain.events import BoundingBox, Event
from ase.domain.evidence import EvidenceItem
from ase.domain.llm import LlmProfile, LlmRole, LlmUsage
from ase.domain.report_records import ReportVersion
from ase.domain.reports import KeyJudgement
from ase.domain.research import CollectionAttempt
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
    seed_events: tuple[Event, ...] = ()
    seed_attempts: tuple[CollectionAttempt, ...] = ()
    reused_evidence: tuple[EvidenceItem, ...] = ()
    followup_judgements: tuple[KeyJudgement, ...] = ()


@dataclass(slots=True)
class Totals:
    """Tokens, latency and findings summed over every model call of one version."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: float = 0.0
    findings: list[Finding] = field(default_factory=list)
    usage: list[LlmUsage] = field(default_factory=list)

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


def usage_entry(job: Job, profile: LlmProfile, purpose: str, ok: bool, call: Any) -> LlmUsage:
    """Prepare call accounting in memory; persist it after all outbound stages finish."""
    findings: Sequence[Finding] = call.findings
    problems = [f.message for f in findings if not ok or f.severity is Severity.ERROR]
    return LlmUsage(
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
