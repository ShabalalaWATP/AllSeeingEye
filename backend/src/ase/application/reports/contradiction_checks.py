"""Say which sources disagree with a judgement, on what, and what kind of sources they are.

The evidence assessment already works out that opposing reporting is as strong as the
support. That tells a reader a judgement is contested without telling them who says
what. This check turns the same frozen metadata into a sentence naming both sides with
their grades and their character. It is mechanical and changes nothing in the report.
"""

from __future__ import annotations

from collections.abc import Sequence

from ase.domain.evidence import EvidenceItem
from ase.domain.evidence_matrix import JudgementAssessment, ReportAssessment
from ase.domain.report_quality_rules import CONTRADICTION_RULE
from ase.domain.reports import ReportBody
from ase.domain.source_requirements import describe_characters
from ase.domain.validation_types import Finding, Severity

MAX_CONTESTED = 6
MAX_LABELS_PER_SIDE = 4


def describe_side(labels: Sequence[str], frozen: dict[str, EvidenceItem]) -> str:
    """Name each cited source with its grade and the kind of source it is."""
    parts = [
        f"{label} ({frozen[label].source_name}, graded {frozen[label].grade}, "
        f"{describe_characters(frozen[label])})"
        for label in labels[:MAX_LABELS_PER_SIDE]
        if label in frozen
    ]
    remaining = len([label for label in labels if label in frozen]) - len(parts)
    if remaining > 0:
        parts.append(f"and {remaining} more")
    return "; ".join(parts)


def _statement(body: ReportBody, judgement_id: str) -> str:
    return next(
        (row.statement for row in body.key_judgements if row.id == judgement_id), judgement_id
    )


def _finding(
    body: ReportBody, row: JudgementAssessment, frozen: dict[str, EvidenceItem]
) -> Finding:
    contested = row.balance == "opposition_at_least_as_strong"
    weight = (
        "The opposing reporting is at least as strong as the support"
        if contested
        else "The opposing reporting is weaker than the support"
    )
    return Finding(
        CONTRADICTION_RULE,
        Severity.ERROR if contested else Severity.WARNING,
        row.judgement_id,
        f"Sources disagree about {row.judgement_id}, “{_statement(body, row.judgement_id)}"
        f"”. Cited in support: {describe_side(row.supporting_labels, frozen)}. "
        f"Cited against: {describe_side(row.contradicting_labels, frozen)}. "
        f"{weight} ({row.support_tier.value} against {row.opposition_tier.value}); "
        "both relationships were assigned by the model and are not independently verified.",
    )


def check_contradictions(
    body: ReportBody, assessment: ReportAssessment | None, evidence: Sequence[EvidenceItem]
) -> list[Finding]:
    """One plain sentence for each judgement whose cited reporting disagrees with itself."""
    if assessment is None:
        return []
    frozen = {item.label: item for item in evidence}
    contested = [row for row in assessment.judgements if row.contradicting_labels]
    return [_finding(body, row, frozen) for row in contested[:MAX_CONTESTED]]
