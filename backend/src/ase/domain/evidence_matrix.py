"""Versioned application evidence policy, not a probability or official grading formula."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

from ase.domain.doctrine import Confidence

METHOD_VERSION = "ase-evidence-v1"


class Contribution(StrEnum):
    STRONG = "strong"
    MODERATE = "moderate"
    LIMITED = "limited"
    UNASSESSED = "unassessed"


CONTRIBUTION_ORDER = {
    Contribution.UNASSESSED: 0,
    Contribution.LIMITED: 1,
    Contribution.MODERATE: 2,
    Contribution.STRONG: 3,
}

LIMITATIONS = (
    "This is an application evidence-strength policy, not an official NATO scoring algorithm "
    "or a probability that a claim is true.",
    "Supporting and opposing relationships are model-assigned; entailment and claim agreement "
    "have not been independently verified.",
    "Declared organisations and possible-copy groups do not establish independent sourcing.",
    "Judgement groups use only model-assigned judgement citations. Unassigned counterevidence "
    "may exist; separate devil's advocacy citations are not classified as opposing evidence.",
    "The engine limits confidence using the information base. It does not measure analytical "
    "rigour, complexity and volatility, or provide a full calibrated analytical confidence rating.",
)


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    label: str
    event_id: str
    source_id: str
    reliability: str
    credibility: int
    contribution: Contribution
    organisation: str | None
    flags: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContributionGroup:
    id: str
    labels: tuple[str, ...]
    known_organisation: bool
    contribution: Contribution
    corroborating_contribution: Contribution
    confirmed_strong: bool
    possible_copy: bool


@dataclass(frozen=True, slots=True)
class JudgementAssessment:
    judgement_id: str
    supporting_labels: tuple[str, ...]
    contradicting_labels: tuple[str, ...]
    invalid_labels: tuple[str, ...]
    support_groups: tuple[ContributionGroup, ...]
    opposition_groups: tuple[ContributionGroup, ...]
    support_tier: Contribution
    opposition_tier: Contribution
    balance: Literal[
        "no_support", "support_only", "support_stronger", "opposition_at_least_as_strong"
    ]
    status: Literal["supported", "limited", "contested", "unsupported"]
    confidence_ceiling: Confidence
    final_confidence: Confidence
    explanation: tuple[str, ...]
    limitations: tuple[str, ...]
    improvements: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AssessmentTallies:
    evidence_items: int
    declared_groups: int
    unknown_provenance_items: int
    possible_copy_groups: int
    judgements: int
    strong: int
    moderate: int
    limited: int
    unassessed: int
    supported_judgements: int
    limited_judgements: int
    contested_judgements: int
    unsupported_judgements: int


@dataclass(frozen=True, slots=True)
class ReportAssessment:
    method_version: str
    evidence: tuple[EvidenceAssessment, ...]
    judgements: tuple[JudgementAssessment, ...]
    tallies: AssessmentTallies
    validation_errors: int
    validation_warnings: int
    limitations: tuple[str, ...]


def contribution_for(reliability: str, credibility: int) -> Contribution:
    """Keep unknown grades distinct from adverse grades; never infer truth from a brand."""
    if reliability not in "ABCDEF" or len(reliability) != 1 or credibility not in range(1, 7):
        return Contribution.UNASSESSED
    if credibility == 6:
        return Contribution.UNASSESSED
    if credibility in (1, 2):
        if reliability in ("A", "B"):
            return Contribution.STRONG
        if reliability in ("C", "F") or credibility == 1:
            return Contribution.MODERATE
    if reliability in ("A", "B") and credibility == 3:
        return Contribution.MODERATE
    return Contribution.LIMITED


def evidence_policy_metadata() -> dict[str, Any]:
    """Public, JSON-safe guide generated from the same matrix used by the engine."""
    return {
        "method_version": METHOD_VERSION,
        "title": "Automated evidence contribution and confidence limits",
        "reliability_scale": [
            {"grade": grade, "label": label}
            for grade, label in zip(
                "ABCDEF",
                (
                    "Completely reliable",
                    "Usually reliable",
                    "Fairly reliable",
                    "Not usually reliable",
                    "Unreliable",
                    "Reliability cannot be judged",
                ),
                strict=True,
            )
        ],
        "credibility_scale": [
            {"grade": grade, "label": label}
            for grade, label in enumerate(
                (
                    "Confirmed by other sources",
                    "Probably true",
                    "Possibly true",
                    "Doubtful",
                    "Improbable",
                    "Truth cannot be judged",
                ),
                start=1,
            )
        ],
        "assessment_dimensions": [
            {
                "name": "Information base",
                "engine_assessed": True,
                "description": "Bounded source/item grades, declared provenance and model-assigned "
                "relationships; source content and entailment are not verified.",
            },
            {
                "name": "Analytical rigour",
                "engine_assessed": False,
                "description": "Structural checks and a model rationale do not establish "
                "analytical rigour.",
            },
            {
                "name": "Complexity and volatility",
                "engine_assessed": False,
                "description": "These subject characteristics are not measured by this "
                "evidence policy.",
            },
        ],
        "contribution_matrix": [
            {
                "reliability": reliability,
                "credibility": credibility,
                "contribution": contribution_for(reliability, credibility).value,
            }
            for reliability in "ABCDEF"
            for credibility in range(1, 7)
        ],
        "confidence_rules": [
            "Count only the strongest eligible contribution in each declared organisation or "
            "possible-copy group. Unknown provenance cannot supply corroboration.",
            "One strong contribution permits moderate confidence. One moderate, limited or "
            "unassessed contribution permits low confidence.",
            "At least two known separate groups with moderate or strong contributions permit "
            "moderate confidence. Weak or duplicate padding cannot raise the limit.",
            "High requires at least two known separate strong groups containing credibility-1 "
            "support, no flagged cited support and no model-cited opposition in that judgement.",
            "Opposition at least as strong as support limits confidence to low. Weaker "
            "opposition limits it to moderate. Relationships remain model-assigned.",
            "A confidence limit cannot raise the model's confidence. Likelihood remains a "
            "separate UK probability-yardstick term; this matrix does not calculate it.",
            "F and 6 mean unassessed, not false. Credibility-1 information from D/E sources "
            "can make a moderate contribution, while its source reliability remains D/E.",
        ],
        "limitations": list(LIMITATIONS),
        "doctrine_references": [
            {
                "title": "PHIA: Explaining uncertainty in UK intelligence assessment "
                "(24 March 2025)",
                "url": "https://www.gov.uk/government/publications/"
                "explaining-uncertainty-in-uk-intelligence-assessment/"
                "explaining-uncertainty-in-uk-intelligence-assessment",
            },
            {
                "title": "PHIA: Common analytical standards (24 March 2025)",
                "url": "https://www.gov.uk/government/publications/phia-common-analytical-standards/"
                "phia-common-analytical-standards",
            },
            {
                "title": "JDP 2-00, fourth edition, table 3.1 and paragraphs 3.39-3.40",
                "url": "https://assets.publishing.service.gov.uk/media/653a4b0780884d0013f71bb0/"
                "JDP_2_00_Ed_4_web.pdf",
            },
        ],
    }
