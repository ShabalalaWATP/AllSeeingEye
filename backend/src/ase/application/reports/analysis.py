"""A second bounded call that writes the implications the drafting call had no room for.

One pass asked to report, judge, warn, list gaps and explain will spend its output on
structure. This stage reads the drafted reporting and the same frozen evidence and
writes the assessment properly, and may request one diagram when structured data carries
something the prose cannot. It is checkpointed under its own digest, metered through the
gateway it is given, and degrades honestly: when the budget, the capability or the model
fails, the report keeps the body it already had and says the analysis pass did not run.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from ase.application.ports.llm import LlmGateway, LlmGatewayError, LlmTokenBudgetExhausted
from ase.application.ports.section_checkpoints import SectionCheckpoint, SectionCheckpoints
from ase.application.reports.analysis_contract import (
    ANALYSIS_SCHEMA,
    AnalysisRejected,
    parse_analysis,
)
from ase.application.reports.depth import depth_for
from ase.application.reports.prompts import (
    ANALYSIS_STANDARD,
    doctrine_preamble,
    evidence_block,
    output_guidance,
    template_guidance,
)
from ase.application.reports.sections.contracts import decode
from ase.application.reports.sections.planning import canonical_json
from ase.application.reports.sections.prompts import PROVENANCE
from ase.application.reports.templates import Template
from ase.domain.evidence import EvidenceItem
from ase.domain.llm import LlmMessage, LlmProfile, LlmRequest
from ase.domain.report_diagrams import ReportDiagram
from ase.domain.reports import AssessmentSection, ReportBody, ReportHeader
from ase.domain.validation import Finding, Severity

MAX_PROMPT_BYTES = 384 * 1024
STAGE_ID = "analysis"
DIAGRAM_GUIDANCE = (
    "Diagram. You may request at most one diagram, and only when structured data carries "
    "something the prose cannot: a timeline of dated events, an actor or relationship "
    "map, a causal or influence chain, a comparison matrix, or a simple quantitative "
    "series over time. Emit structured data only, never drawing, layout, colour or "
    "styling instructions; the application draws it. Every node, edge, entry, row and "
    "series must cite the frozen evidence it rests on, and may carry only what that "
    "evidence states. Do not compute, convert, scale or estimate a number that the "
    "evidence does not give. Use null when a diagram would be trivial, decorative, or "
    "unsupported by at least three distinct pieces of evidence: an absent diagram is "
    "always better than a misleading one."
)


@dataclass(slots=True)
class AnalysisOutcome:
    """What the pass produced, and enough accounting for the usage ledger."""

    sections: tuple[AssessmentSection, ...] = ()
    diagram: ReportDiagram | None = None
    diagram_reason: str = ""
    performed: bool = False
    skipped_reason: str = ""
    model: str = ""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    latency_ms: float = 0.0
    attempts: int = 0
    findings: list[Finding] = field(default_factory=list)

    def apply(self, body: ReportBody) -> ReportBody:
        """Append the analysis as assessment; reporting and judgements are untouched."""
        if not self.sections and self.diagram is None:
            return body
        return replace(
            body,
            assessment=body.assessment + self.sections,
            diagrams=(self.diagram,) if self.diagram is not None else body.diagrams,
        )


def analysis_digest(
    profile: LlmProfile, template: Template, header: ReportHeader, body: ReportBody, evidence: Any
) -> str:
    packet = canonical_json(
        {
            "stage": "report-analysis-v1",
            "profile": profile.config_hash,
            "template": asdict(template),
            "header": asdict(header),
            "reporting": [asdict(theme) for theme in body.reporting],
            "assessment": [asdict(section) for section in body.assessment],
            "evidence": [item.label for item in evidence],
        }
    )
    return hashlib.sha256(packet.encode("utf-8")).hexdigest()


async def run_analysis(  # noqa: PLR0911 - one bounded stage with several honest exits
    gateway: LlmGateway,
    profile: LlmProfile,
    api_key: str,
    template: Template,
    header: ReportHeader,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
    *,
    question: str | None = None,
    background: str | None = None,
    checkpoints: SectionCheckpoints | None = None,
) -> AnalysisOutcome:
    """Run the pass, or say honestly why it did not run. Never raises on model failure."""
    if template.analysis_budget <= 0:
        return AnalysisOutcome(skipped_reason="this product does not run an analysis pass")
    if not evidence or not body.reporting:
        return AnalysisOutcome(skipped_reason="no drafted reporting to analyse")
    labels = frozenset(item.label for item in evidence)
    urls = {item.label: item.url for item in evidence}
    digest = analysis_digest(profile, template, header, body, evidence)
    saved = await _saved(checkpoints, digest, labels, urls)
    if saved is not None:
        return saved
    try:
        messages = _messages(template, header, body, evidence, question, background)
    except ValueError as exc:
        return AnalysisOutcome(skipped_reason=str(exc)[:200])
    outcome = AnalysisOutcome(model=profile.model, attempts=1)
    started = time.perf_counter()
    try:
        result = await gateway.complete(
            profile.base_url,
            api_key,
            profile.model,
            LlmRequest(
                messages=messages,
                max_output_tokens=profile.token_budget(template.analysis_budget),
                temperature=profile.temperature,
                reasoning_effort=profile.reasoning_effort,
                provider=profile.provider,
                profile_id=profile.id,
                json_schema=ANALYSIS_SCHEMA,
                schema_name="report_analysis",
            ),
        )
    except LlmTokenBudgetExhausted as exc:
        outcome.latency_ms = max(0.0, (time.perf_counter() - started) * 1000)
        outcome.prompt_tokens, outcome.completion_tokens = exc.prompt_tokens, exc.completion_tokens
        return _degraded(outcome, "the analysis pass exhausted its token allowance")
    except LlmGatewayError as exc:
        outcome.latency_ms = max(0.0, (time.perf_counter() - started) * 1000)
        return _degraded(outcome, f"the analysis pass could not be completed: {exc}"[:200])
    outcome.model = result.model or profile.model
    outcome.prompt_tokens = result.prompt_tokens
    outcome.completion_tokens = result.completion_tokens
    outcome.latency_ms = result.latency_ms
    try:
        value = decode(result.content)
        sections, diagram, reason = parse_analysis(value, labels, urls)
    except (AnalysisRejected, ValueError, TypeError, RecursionError) as exc:
        return _degraded(outcome, f"the analysis pass did not fit its contract: {exc}"[:200])
    outcome.sections, outcome.diagram, outcome.diagram_reason = sections, diagram, reason
    outcome.performed = True
    _record_diagram(outcome)
    if checkpoints is not None:
        await _save(checkpoints, digest, value)
    return outcome


def _record_diagram(outcome: AnalysisOutcome) -> None:
    if outcome.diagram_reason:
        outcome.findings.append(
            Finding(
                "diagram",
                Severity.WARNING,
                "analysis",
                f"A requested diagram was not shown: {outcome.diagram_reason}",
            )
        )


def _degraded(outcome: AnalysisOutcome, reason: str) -> AnalysisOutcome:
    outcome.performed = False
    outcome.skipped_reason = reason
    outcome.findings.append(Finding("analysis", Severity.WARNING, "analysis", reason))
    return outcome


async def _saved(
    checkpoints: SectionCheckpoints | None,
    digest: str,
    labels: frozenset[str],
    urls: dict[str, str | None],
) -> AnalysisOutcome | None:
    """Reuse an identical completed pass; a payload that no longer validates is discarded."""
    if checkpoints is None:
        return None
    checkpoint = await checkpoints.load(digest, STAGE_ID)
    if checkpoint is None or checkpoint.status != "completed" or not checkpoint.payload:
        return None
    try:
        sections, diagram, reason = parse_analysis(checkpoint.payload["body"], labels, urls)
    except (AnalysisRejected, ValueError, TypeError, KeyError, RecursionError):
        return None
    outcome = AnalysisOutcome(
        sections=sections, diagram=diagram, diagram_reason=reason, performed=True
    )
    _record_diagram(outcome)
    return outcome


async def _save(checkpoints: SectionCheckpoints, digest: str, value: Any) -> None:
    await checkpoints.save(
        digest, STAGE_ID, SectionCheckpoint(status="completed", payload={"body": value})
    )


def _messages(
    template: Template,
    header: ReportHeader,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
    question: str | None,
    background: str | None,
) -> tuple[LlmMessage, ...]:
    depth = depth_for(header.scope.get("research_mode"))
    system = "\n".join(
        part
        for part in (
            doctrine_preamble(),
            template_guidance(template),
            ANALYSIS_STANDARD,
            DIAGRAM_GUIDANCE,
            PROVENANCE,
            output_guidance(
                str(header.scope.get("report_language", "en")),
                str(header.scope.get("report_style", "assessment")),
            ),
            depth.guidance() if depth is not None else "",
            "This call writes ONLY the assessment sections and an optional diagram. The "
            "reporting, key judgements, warning, gaps and sourcing are already written and "
            "are supplied as unverified generated context: do not rewrite, contradict or "
            "restate them. Write one section per analytical line of argument, each with a "
            "heading naming the argument rather than the theme, and cite the exact frozen "
            "evidence IDs each section rests on. If the drafted reporting cannot support "
            "analysis, write one short honest section saying so and request no diagram.",
        )
        if part
    )
    data: dict[str, Any] = {
        "product": {"title": template.title, "purpose": template.purpose},
        "analytical_questions": list(template.analysis_focus),
        "header": asdict(header),
        "question": question,
        "background_context_not_evidence": background,
        "drafted_reporting_not_evidence": [asdict(theme) for theme in body.reporting],
        "drafted_assessment_not_evidence": [asdict(row) for row in body.assessment],
        "drafted_judgements_not_evidence": [asdict(row) for row in body.key_judgements],
        "original_frozen_evidence": [evidence_block(item) for item in evidence],
    }
    content = canonical_json(data)
    if len((system + content).encode("utf-8")) > MAX_PROMPT_BYTES:
        raise ValueError("the analysis packet exceeds its bounded input size")
    return (LlmMessage("system", system), LlmMessage("user", content))
