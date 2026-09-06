"""Inspect frozen judgements without extracting new claims or rerunning scoring policy."""

from dataclasses import dataclass
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from ase.domain.citation_checks import JudgementCitationCheck
from ase.domain.evidence_matrix import JudgementAssessment
from ase.domain.report_records import ReportVersion


@dataclass(frozen=True, slots=True)
class ClaimDimension:
    name: Literal["evidence_support", "source_independence", "coverage", "citation_validity"]
    status: str
    explanation: str


@dataclass(frozen=True, slots=True)
class ClaimSource:
    label: str
    relation: Literal["supporting", "contradicting"]
    evidence_id: str | None
    source_name: str | None
    organisation: str | None
    content_hash: str | None


@dataclass(frozen=True, slots=True)
class LedgerClaim:
    id: str
    judgement_id: str
    statement: str
    kind: Literal["analytical_inference"]
    confidence_statement: str
    assumptions: tuple[str, ...]
    sources: tuple[ClaimSource, ...]
    assessment: JudgementAssessment | None
    citation_checks: JudgementCitationCheck | None
    dimensions: tuple[ClaimDimension, ...]


@dataclass(frozen=True, slots=True)
class ClaimLedger:
    derivation_version: str
    report_version: int
    claims: tuple[LedgerClaim, ...]
    recorded_gaps: tuple[str, ...]
    limitations: tuple[str, ...]


def _dimensions(
    assessment: JudgementAssessment | None, check: JudgementCitationCheck | None
) -> tuple[ClaimDimension, ...]:
    groups = (
        {group.id: group for group in (*assessment.support_groups, *assessment.opposition_groups)}
        if assessment
        else {}
    )
    return (
        ClaimDimension(
            "evidence_support",
            assessment.status if assessment else "unknown",
            "Saved evidence assessment; support/opposition relationships were model-assigned. "
            "No current scoring policy has been applied."
            if assessment
            else "No assessment was saved for this judgement.",
        ),
        ClaimDimension(
            "source_independence",
            "declared_only" if groups else "unknown",
            f"{len(groups)} saved organisation/possible-copy groups; "
            f"{sum(group.possible_copy for group in groups.values())} possible-copy groups. "
            "These groups do not verify independent reporting or an original-source chain."
            if groups
            else "No source groups were saved for this judgement.",
        ),
        ClaimDimension(
            "coverage",
            "unknown",
            "Completeness against the research question is not measured. Report-level gaps "
            "are retained separately; no gaps recorded does not establish complete coverage.",
        ),
        ClaimDimension(
            "citation_validity",
            check.status.value if check else "unknown",
            "Saved literal excerpt checks only. Excerpt presence does not verify support "
            "or truth; mismatch indicators do not establish contradiction."
            if check
            else "No citation checks were saved for this judgement.",
        ),
    )


def build_claim_ledger(version: ReportVersion) -> ClaimLedger:
    """Version-scoped IDs retain existing judgement boundaries, including compound ones."""
    assessments = (
        {item.judgement_id: item for item in version.assessment.judgements}
        if version.assessment
        else {}
    )
    checks = (
        {item.judgement_id: item for item in version.citation_checks.judgements}
        if version.citation_checks
        else {}
    )
    evidence = {item.label: item for item in version.evidence}
    claims = []
    for judgement in version.body.key_judgements:
        sources = []
        relations: tuple[tuple[Literal["supporting", "contradicting"], tuple[str, ...]], ...] = (
            ("supporting", judgement.supporting_evidence),
            ("contradicting", judgement.contradicting_evidence),
        )
        for relation, labels in relations:
            for label in dict.fromkeys(labels):
                item = evidence.get(label)
                sources.append(
                    ClaimSource(
                        label,
                        relation,
                        item.event_id if item else None,
                        item.source_name if item else None,
                        (item.independence_key.strip() or None) if item else None,
                        (item.content_hash or None) if item else None,
                    )
                )
        assessment, check = assessments.get(judgement.id), checks.get(judgement.id)
        claims.append(
            LedgerClaim(
                id=str(uuid5(NAMESPACE_URL, f"ase:claim:{version.id}:{judgement.id}")),
                judgement_id=judgement.id,
                statement=judgement.statement,
                kind="analytical_inference",
                confidence_statement=judgement.confidence_statement,
                assumptions=judgement.assumptions,
                sources=tuple(sources),
                assessment=assessment,
                citation_checks=check,
                dimensions=_dimensions(assessment, check),
            )
        )
    return ClaimLedger(
        "ase-claim-inspection-v1",
        version.number,
        tuple(claims),
        tuple(gap.text for gap in version.body.gaps),
        (
            "Each entry retains one saved judgement, not an independently extracted atomic claim.",
            "IDs identify this frozen report version; they do not assert identity across versions.",
            "Relationships are model-assigned. Original-source chains remain unverified.",
            "Missing historical assessments remain unknown. No truth score is calculated.",
        ),
    )
