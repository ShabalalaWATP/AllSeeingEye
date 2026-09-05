"""The model loop for one report version: compose, call, parse, validate, retry once."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field

from ase.application.ports.llm import LlmGateway, LlmGatewayError
from ase.application.reports.prompts import compose_messages
from ase.application.reports.templates import Template
from ase.domain.direction import Direction
from ase.domain.evidence import EvidenceItem, QualityOfInformation
from ase.domain.llm import LlmProfile, LlmRequest
from ase.domain.report_schema import REPORT_BODY_SCHEMA
from ase.domain.reports import KeyJudgement, ReportBody, ReportHeader, ReportParseError, parse_body
from ase.domain.validation import Finding, Severity, validate_body

MAX_ATTEMPTS = 2


@dataclass(slots=True)
class Draft:
    body: ReportBody | None = None
    findings: list[Finding] = field(default_factory=list)
    model: str = ""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: float = 0.0
    attempts: int = 0

    @property
    def has_errors(self) -> bool:
        return any(f.severity is Severity.ERROR for f in self.findings)


async def draft_body(
    gateway: LlmGateway,
    profile: LlmProfile,
    api_key: str,
    template: Template,
    header: ReportHeader,
    question: str | None,
    quality: QualityOfInformation,
    evidence: Sequence[EvidenceItem],
    previous: Sequence[KeyJudgement],
    direction: Direction | None = None,
) -> Draft:
    """Ask the model up to twice; the second attempt quotes the validator's findings back."""
    draft = Draft()
    labels = frozenset(item.label for item in evidence)
    urls = {item.label: item.url for item in evidence}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        draft.attempts = attempt
        messages = compose_messages(
            template,
            scope_line=header.title,
            period_from=header.period_from,
            period_to=header.period_to,
            question=question,
            quality=quality,
            evidence=evidence,
            findings=draft.findings,
            previous=previous,
            direction=direction,
        )
        llm_request = LlmRequest(
            messages=messages,
            max_output_tokens=min(profile.max_output_tokens, template.token_budget),
            temperature=profile.temperature,
            json_schema=REPORT_BODY_SCHEMA,
            schema_name="report",
        )
        try:
            result = await gateway.complete(profile.base_url, api_key, profile.model, llm_request)
        except LlmGatewayError as exc:
            draft.findings = [Finding("model", Severity.ERROR, "gateway", str(exc))]
            continue
        draft.model = result.model
        draft.prompt_tokens = (draft.prompt_tokens or 0) + (result.prompt_tokens or 0)
        draft.completion_tokens = (draft.completion_tokens or 0) + (result.completion_tokens or 0)
        draft.latency_ms += result.latency_ms
        try:
            parsed = parse_body(json.loads(result.content))
        except (ValueError, ReportParseError) as exc:
            draft.findings = [Finding("schema", Severity.ERROR, "output", f"{exc}"[:300])]
            continue
        validated = validate_body(
            parsed,
            labels,
            urls,
            confidence_ceiling=quality.confidence_ceiling,
            previous_exists=bool(previous),
        )
        draft.body = validated.body
        draft.findings = list(validated.findings)
        if validated.passed:
            break
    return draft
