"""The model loop for one report version: compose, call, parse, validate, retry once."""

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

from ase.application.ports.llm import LlmGateway, LlmGatewayError, LlmTokenBudgetExhausted
from ase.application.reports.prompts import compose_messages
from ase.application.reports.templates import Template
from ase.domain.direction import Direction
from ase.domain.evidence import EvidenceItem, QualityOfInformation
from ase.domain.llm import LlmProfile, LlmRequest
from ase.domain.report_input import parse_model_body
from ase.domain.report_schema import REPORT_BODY_SCHEMA
from ase.domain.reports import KeyJudgement, ReportBody, ReportHeader, ReportParseError
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
    supported_requirements: frozenset[str] | None = None

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
    background: str | None = None,
) -> Draft:
    """Retry repairable failures once, but never repeat an exhausted token budget."""
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
            data_cutoff=header.data_cutoff,
            question=question,
            quality=quality,
            evidence=evidence,
            findings=draft.findings,
            previous=previous,
            direction=direction,
            background=background,
            report_language=str(header.scope.get("report_language", "en")),
            report_style=str(header.scope.get("report_style", "assessment")),
        )
        llm_request = LlmRequest(
            messages=messages,
            max_output_tokens=profile.token_budget(template.token_budget),
            temperature=profile.temperature,
            reasoning_effort=profile.reasoning_effort,
            provider=profile.provider,
            profile_id=profile.id,
            json_schema=REPORT_BODY_SCHEMA,
            schema_name="report",
        )
        started = time.perf_counter()
        try:
            result = await gateway.complete(profile.base_url, api_key, profile.model, llm_request)
        except LlmTokenBudgetExhausted as exc:
            draft.body = None
            draft.model = exc.model or draft.model
            if exc.prompt_tokens is not None:
                draft.prompt_tokens = (draft.prompt_tokens or 0) + exc.prompt_tokens
            if exc.completion_tokens is not None:
                draft.completion_tokens = (draft.completion_tokens or 0) + exc.completion_tokens
            draft.latency_ms += max(0.0, (time.perf_counter() - started) * 1000)
            draft.findings = [Finding("model", Severity.ERROR, "gateway", str(exc))]
            break
        except LlmGatewayError as exc:
            draft.findings = [Finding("model", Severity.ERROR, "gateway", str(exc))]
            continue
        draft.model = result.model
        draft.prompt_tokens = (draft.prompt_tokens or 0) + (result.prompt_tokens or 0)
        draft.completion_tokens = (draft.completion_tokens or 0) + (result.completion_tokens or 0)
        draft.latency_ms += result.latency_ms
        try:
            parsed = parse_model_body(json.loads(result.content))
        except RecursionError:
            draft.findings = [
                Finding("schema", Severity.ERROR, "output", "Model JSON is nested too deeply.")
            ]
            continue
        except (ValueError, ReportParseError) as exc:
            draft.findings = [Finding("schema", Severity.ERROR, "output", f"{exc}"[:300])]
            continue
        validated = validate_body(
            parsed,
            labels,
            urls,
            previous_exists=bool(previous),
            evidence_items=evidence,
        )
        draft.body = validated.body
        draft.findings = list(validated.findings)
        if validated.passed:
            break
    return draft
