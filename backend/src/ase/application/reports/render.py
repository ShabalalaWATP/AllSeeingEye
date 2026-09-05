"""Markdown rendering of a report: judgements first, evidence annex last, nothing invented."""

from __future__ import annotations

from collections.abc import Sequence

from ase.domain.doctrine import term_for
from ase.domain.evidence import EvidenceItem, QualityOfInformation
from ase.domain.reports import ReportBody, ReportHeader
from ase.domain.validation import Finding


def _cites(labels: Sequence[str]) -> str:
    return f" [{', '.join(labels)}]" if labels else ""


def _header_lines(header: ReportHeader) -> list[str]:
    lines = [f"# {header.title}", ""]
    lines.append(
        f"Template: {header.template}. Period {header.period_from:%Y-%m-%d %H:%M} to "
        f"{header.period_to:%Y-%m-%d %H:%M} UTC. "
        f"Data cut-off {header.data_cutoff:%Y-%m-%d %H:%M} UTC."
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
        lines.append(
            f"  Probability: {term_for(judgement.probability)}. "
            f"Confidence: {judgement.confidence.value}. {judgement.confidence_statement}"
        )
        if judgement.contradicting_evidence:
            contradicting = ", ".join(judgement.contradicting_evidence)
            lines.append(f"  Contradicting evidence: {contradicting}.")
        if judgement.indicators:
            lines.append(f"  Indicators: {'; '.join(judgement.indicators)}.")
        if judgement.change_from_previous is not None:
            lines.append(f"  Change from previous: {judgement.change_from_previous.value}.")
    lines.append("")
    return lines


def _analysis_lines(body: ReportBody) -> list[str]:
    lines: list[str] = []
    if body.reporting:
        lines += ["## Reporting", ""]
        for theme in body.reporting:
            lines.append(f"### {theme.theme}")
            for item in theme.items:
                grade = f" ({item.grade})" if item.grade else ""
                lines.append(f"- {item.text}{_cites(item.evidence)}{grade}")
            lines.append("")
    if body.assessment:
        lines += ["## Assessment", ""]
        for section in body.assessment:
            lines += [f"### {section.heading}", f"{section.text}{_cites(section.evidence)}", ""]
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


def _annex_lines(
    evidence: Sequence[EvidenceItem], quality: QualityOfInformation, findings: Sequence[Finding]
) -> list[str]:
    lines = ["## Quality of information", "", quality.describe(), ""]
    if findings:
        lines += ["## Validator findings", ""]
        lines.extend(f"- {f.severity.value}: {f.location}: {f.message}" for f in findings)
        lines.append("")
    lines += ["## Evidence annex", ""]
    lines.append("| Label | Grade | Source | Published | Title | Link |")
    lines.append("|---|---|---|---|---|---|")
    for item in evidence:
        title = item.title.replace("|", "\\|")
        link = f"[link]({item.url})" if item.url else ""
        lines.append(
            f"| {item.label} | {item.grade} | {item.source_name} | "
            f"{item.published_at:%Y-%m-%d %H:%M} | {title} | {link} |"
        )
    lines.append("")
    return lines


def render_markdown(
    header: ReportHeader,
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
    quality: QualityOfInformation,
    findings: Sequence[Finding] = (),
) -> str:
    lines = (
        _header_lines(header)
        + _judgement_lines(body)
        + _analysis_lines(body)
        + _closing_lines(body)
        + _annex_lines(evidence, quality, findings)
    )
    return "\n".join(lines)
