"""Markdown rendering of a report: judgements first, evidence annex last, nothing invented."""

from __future__ import annotations

from collections.abc import Sequence

from ase.application.reports.assessment_export import assessment_sections
from ase.application.reports.challenge_export import challenge_sections
from ase.application.reports.citation_export import citation_sections
from ase.application.reports.context_export import context_sections
from ase.application.reports.diagram_text import diagram_lines
from ase.application.reports.export_text import markdown_fields, plain_markdown, review_notice
from ase.application.reports.markdown_annex import annex_lines
from ase.application.reports.research_export import research_sections
from ase.application.reports.web_research_export import web_context_markdown
from ase.domain.advocacy import DevilsAdvocacy
from ase.domain.challenge import ReportChallenge
from ase.domain.citation_checks import ReportCitationChecks
from ase.domain.direction import Direction
from ase.domain.doctrine import term_for
from ase.domain.evidence import EvidenceItem, QualityOfInformation
from ase.domain.evidence_matrix import ReportAssessment
from ase.domain.reports import ReportBody, ReportHeader, ReportStatus
from ase.domain.research_context import ResearchContext
from ase.domain.research_records import ResearchReceipt
from ase.domain.validation import Finding


def _cites(labels: Sequence[str]) -> str:
    return f" [{', '.join(labels)}]" if labels else ""


def _direction_lines(direction: Direction | None) -> list[str]:
    if direction is None:
        return []
    lines = ["## Direction", ""]
    lines.extend(f"- {line}" for line in direction.lines())
    if direction.search_terms:
        lines.append(f"- Search terms: {', '.join(direction.search_terms)}")
    lines.append("")
    return lines


def _advocacy_lines(advocacy: DevilsAdvocacy | None) -> list[str]:
    if advocacy is None:
        return []
    lines = ["## Devil's advocacy", ""]
    lines.append(
        f"Contrarian view on {advocacy.target}: {advocacy.argument}{_cites(advocacy.evidence)}"
    )
    lines.append("")
    if advocacy.confidence_before is not None and advocacy.confidence_after is not None:
        lines.append(
            f"Confidence on {advocacy.target} lowered from {advocacy.confidence_before.value} "
            f"to {advocacy.confidence_after.value}. {advocacy.rationale}".rstrip()
        )
    else:
        lines.append(f"Confidence unchanged. {advocacy.rationale}".rstrip())
    lines.append("")
    return lines


def _header_lines(header: ReportHeader, period_line: str | None = None) -> list[str]:
    lines = [f"# {header.title}", ""]
    lines.append(
        plain_markdown(period_line)
        if period_line
        else (
            f"Template: {header.template}. Period {header.period_from:%Y-%m-%d %H:%M} to "
            f"{header.period_to:%Y-%m-%d %H:%M} UTC. "
            f"Data cut-off {header.data_cutoff:%Y-%m-%d %H:%M} UTC."
        )
    )
    if header.requirements:
        lines.append(f"Requirements: {', '.join(header.requirements)}.")
    lines.append("")
    return lines


def _judgement_lines(body: ReportBody) -> list[str]:
    if not body.key_judgements:
        return []
    lines = ["## Key judgements", ""]
    for judgement in body.key_judgements:
        cites = _cites(judgement.supporting_evidence)
        lines.append(f"- **{judgement.id}.** {judgement.statement}{cites}")
        # A blank line before each continuation keeps it a paragraph of its own; a
        # bare indented line would be folded into the statement wherever this renders.
        lines += [
            "",
            f"  Probability: {term_for(judgement.probability)}. "
            f"Confidence: {judgement.confidence.value}. {judgement.confidence_statement}",
        ]
        if judgement.contradicting_evidence:
            contradicting = ", ".join(judgement.contradicting_evidence)
            lines += ["", f"  Contradicting evidence: {contradicting}."]
        if judgement.indicators:
            lines += ["", f"  Indicators: {'; '.join(judgement.indicators)}."]
        if judgement.change_from_previous is not None:
            lines += ["", f"  Change from previous: {judgement.change_from_previous.value}."]
        lines.append("")
    return lines


def _analysis_lines(body: ReportBody) -> list[str]:
    lines: list[str] = []
    if body.reporting:
        lines += ["## Reporting", ""]
        for theme in body.reporting:
            lines += [f"### {theme.theme}", ""]
            for item in theme.items:
                grade = f" ({item.grade})" if item.grade else ""
                lines.append(f"- {item.text}{_cites(item.evidence)}{grade}")
            lines.append("")
    if body.assessment:
        lines += ["## Assessment", ""]
        for section in body.assessment:
            lines += [
                f"### {section.heading}",
                "",
                f"{section.text}{_cites(section.evidence)}",
                "",
            ]
    if body.diagrams:
        lines += ["## Diagrams", ""]
        for diagram in body.diagrams:
            lines += diagram_lines(diagram)
    if body.assumptions:
        lines += ["## Assumptions", ""]
        for assumption in body.assumptions:
            flag = " (lynchpin)" if assumption.lynchpin else ""
            lines.append(f"- **{assumption.id}.** {assumption.text}{flag}")
        lines.append("")
    if body.alternative_hypotheses:
        lines += ["## Alternative hypotheses", ""]
        for alternative in body.alternative_hypotheses:
            lines.append(
                f"- {alternative.text}{_cites(alternative.evidence)} Why less likely: "
                f"{alternative.why_less_likely}"
            )
        lines.append("")
    return lines


def _closing_lines(body: ReportBody) -> list[str]:
    lines = ["## Indicators and warning", ""]
    lines.append(f"Watch condition: {body.indicators_and_warning.watch_condition.value}.")
    if body.indicators_and_warning.changes:
        lines.append("")
        lines.extend(f"- {change}" for change in body.indicators_and_warning.changes)
    lines.append("")
    if body.gaps or body.collection_recommendations:
        lines += ["## Gaps and collection", ""]
        for gap in body.gaps:
            prefix = f"{gap.eei}: " if gap.eei else ""
            lines.append(f"- {prefix}{gap.text}")
        lines.extend(f"- Recommend: {item}" for item in body.collection_recommendations)
        lines.append("")
    lines += ["## Sourcing statement", "", body.sourcing_statement or "Not provided.", ""]
    return lines


def render_markdown(
    header: ReportHeader,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
    quality: QualityOfInformation,
    findings: Sequence[Finding] = (),
    *,
    direction: Direction | None = None,
    advocacy: DevilsAdvocacy | None = None,
    status: ReportStatus | None = None,
    period_line: str | None = None,
    assessment: ReportAssessment | None = None,
    citation_checks: ReportCitationChecks | None = None,
    research: ResearchReceipt | None = None,
    challenge: ReportChallenge | None = None,
    research_context: ResearchContext | None = None,
) -> str:
    header, body = markdown_fields(header), markdown_fields(body)
    direction, advocacy = markdown_fields(direction), markdown_fields(advocacy)
    lines = [
        *_header_lines(header, period_line),
        review_notice(status),
        "",
        *_direction_lines(direction),
        *_judgement_lines(body),
        *_analysis_lines(body),
        *_advocacy_lines(advocacy if challenge is None else None),
        *_closing_lines(body),
        *web_context_markdown(research.web_research if research else None),
        *[
            line
            for title, paragraphs in (
                *assessment_sections(assessment),
                *citation_sections(citation_checks),
                *research_sections(research, include_web=False),
                *challenge_sections(challenge),
                *context_sections(research_context),
            )
            for line in (
                f"## {plain_markdown(title)}",
                "",
                *[plain_markdown(paragraph) for paragraph in paragraphs],
                "",
            )
        ],
        *annex_lines(evidence, quality, findings),
    ]
    return _tidy(lines)


def _tidy(lines: list[str]) -> str:
    """Portable, diff-friendly Markdown: no runs of blank lines, no trailing spaces.

    Renderers treat one blank line and three alike, but a diff does not, so the same
    report content produces the same file every time.
    """
    output: list[str] = []
    for line in lines:
        stripped = line.rstrip()
        if stripped or (output and output[-1]):
            output.append(stripped)
    while output and not output[-1]:
        output.pop()
    return "\n".join(output) + "\n"
