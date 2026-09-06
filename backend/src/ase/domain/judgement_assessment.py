"""Pure evidence assessment from frozen items and model-assigned citation relationships."""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations
from typing import TYPE_CHECKING, Literal

from ase.domain.doctrine import Confidence
from ase.domain.event_similarity import COPY_SIMILARITY, jaccard, text_tokens
from ase.domain.evidence_matrix import (
    CONTRIBUTION_ORDER,
    LIMITATIONS,
    METHOD_VERSION,
    AssessmentTallies,
    Contribution,
    ContributionGroup,
    EvidenceAssessment,
    JudgementAssessment,
    ReportAssessment,
    contribution_for,
)
from ase.domain.source_provenance import ProvenanceItem, organisation_groups

if TYPE_CHECKING:
    from ase.domain.evidence import EvidenceItem
    from ase.domain.reports import KeyJudgement, ReportBody
    from ase.domain.validation_types import Finding


def _organisation(item: EvidenceItem) -> str | None:
    return item.independence_key.strip() or None


def _tier(item: EvidenceItem) -> Contribution:
    return contribution_for(item.reliability, item.credibility)


def _strongest(tiers: Sequence[Contribution]) -> Contribution:
    return max(tiers, key=CONTRIBUTION_ORDER.__getitem__, default=Contribution.UNASSESSED)


def _possible_copy(items: Sequence[EvidenceItem]) -> bool:
    return any(
        (bool(a.content_hash) and a.content_hash == b.content_hash)
        or jaccard(text_tokens(a.title_en or a.title), text_tokens(b.title_en or b.title))
        >= COPY_SIMILARITY
        for a, b in combinations(items, 2)
    )


def _group_index(items: Sequence[EvidenceItem]) -> dict[str, str]:
    ordered = sorted({item.label: item for item in items}.values(), key=lambda item: item.label)
    provenance = organisation_groups(
        [
            ProvenanceItem(
                item.label, _organisation(item), item.title_en or item.title, item.content_hash
            )
            for item in ordered
        ]
    )
    members: dict[str, list[str]] = {}
    for label, group in provenance.group_of.items():
        members.setdefault(group, []).append(label)
    # Stable IDs do not expose the union-find's input-order-dependent representative.
    canonical = {group: f"G:{min(labels)}" for group, labels in members.items()}
    return {label: canonical[group] for label, group in provenance.group_of.items()}


def _groups(items: Sequence[EvidenceItem], index: dict[str, str]) -> tuple[ContributionGroup, ...]:
    grouped: dict[str, list[EvidenceItem]] = {}
    for item in items:
        grouped.setdefault(index[item.label], []).append(item)
    return tuple(
        ContributionGroup(
            id=id_,
            labels=tuple(sorted(item.label for item in members)),
            known_organisation=any(_organisation(item) for item in members),
            contribution=_strongest([_tier(item) for item in members]),
            corroborating_contribution=_strongest(
                [_tier(item) for item in members if _organisation(item)]
            ),
            confirmed_strong=any(
                _organisation(item)
                and _tier(item) is Contribution.STRONG
                and item.credibility == 1
                and not item.flags
                for item in members
            ),
            possible_copy=_possible_copy(members),
        )
        for id_, members in sorted(grouped.items())
    )


def _support_ceiling(
    groups: Sequence[ContributionGroup], items: Sequence[EvidenceItem]
) -> Confidence:
    strong = any(group.contribution is Contribution.STRONG for group in groups)
    corroborating = sum(
        CONTRIBUTION_ORDER[group.corroborating_contribution]
        >= CONTRIBUTION_ORDER[Contribution.MODERATE]
        for group in groups
    )
    if sum(group.confirmed_strong for group in groups) >= 2 and not any(
        item.flags for item in items
    ):
        return Confidence.HIGH
    return Confidence.MODERATE if strong or corroborating >= 2 else Confidence.LOW


def evidence_confidence_ceiling(items: Sequence[EvidenceItem]) -> Confidence:
    """Compatibility summary for a set treated as support, never a whole-report limit."""
    unique = tuple({item.label: item for item in items}.values())
    return _support_ceiling(_groups(unique, _group_index(unique)), unique)


def assess_judgement(
    judgement: KeyJudgement,
    evidence: Sequence[EvidenceItem],
) -> JudgementAssessment:
    frozen = {item.label: item for item in evidence}
    support_labels = tuple(sorted(set(judgement.supporting_evidence) & frozen.keys()))
    opposing_labels = tuple(sorted(set(judgement.contradicting_evidence) & frozen.keys()))
    invalid = tuple(
        sorted(
            (set(judgement.supporting_evidence) | set(judgement.contradicting_evidence))
            - frozen.keys()
        )
    )
    support = [frozen[label] for label in support_labels]
    opposition = [frozen[label] for label in opposing_labels]
    index = _group_index([*support, *opposition])
    support_groups, opposition_groups = _groups(support, index), _groups(opposition, index)
    support_tier = _strongest([group.contribution for group in support_groups])
    opposition_tier = _strongest([group.contribution for group in opposition_groups])
    ceiling = _support_ceiling(support_groups, support)
    balance: Literal[
        "no_support", "support_only", "support_stronger", "opposition_at_least_as_strong"
    ]
    balance = "support_only" if support else "no_support"
    reasons = [
        f"Supporting contribution: {support_tier.value}; "
        f"opposing contribution: {opposition_tier.value}.",
        "Only the strongest contribution per declared organisation or possible-copy group counts.",
    ]
    if opposition:
        if CONTRIBUTION_ORDER[opposition_tier] >= CONTRIBUTION_ORDER[support_tier]:
            ceiling, balance = Confidence.LOW, "opposition_at_least_as_strong"
            reasons.append(
                "Model-assigned opposition is at least as strong as support, "
                "limiting confidence to low."
            )
        else:
            ceiling = Confidence.LOW if ceiling is Confidence.LOW else Confidence.MODERATE
            balance = "support_stronger"
            reasons.append(
                "Model-assigned opposition is weaker than support, but prevents a high ceiling."
            )
    status: Literal["supported", "limited", "contested", "unsupported"]
    status = (
        "unsupported"
        if support_tier is Contribution.UNASSESSED
        else (
            "contested" if opposition else "limited" if ceiling is Confidence.LOW else "supported"
        )
    )
    reasons.append(
        f"Evidence confidence ceiling: {ceiling.value}. This cannot raise model confidence."
    )
    limits = list(LIMITATIONS)
    improvements: list[str] = []
    if invalid:
        limits.append(f"Unknown evidence labels excluded: {', '.join(invalid)}.")
        improvements.append("Replace unknown citations with identifiable frozen evidence.")
    if not support or support_tier is Contribution.UNASSESSED:
        improvements.append("Obtain assessable evidence directly addressing this judgement.")
    if ceiling is Confidence.LOW and support:
        improvements.append(
            "Seek stronger item-level evidence; additional weak reports do not raise the ceiling."
        )
    if any(not _organisation(item) for item in [*support, *opposition]):
        limits.append("Some cited provenance is unknown and cannot establish corroboration.")
        improvements.append("Establish the origin and provenance of the cited reporting.")
    if len([group for group in support_groups if group.known_organisation]) < 2:
        improvements.append("Seek a separate reporting chain with moderate or stronger evidence.")
    if opposition:
        improvements.append("Resolve the conflicting claims using additional direct evidence.")
    if any(item.flags for item in [*support, *opposition]):
        limits.append(
            "Cited source cautions remain relevant; an official or interested source "
            "is not automatically correct."
        )
    return JudgementAssessment(
        judgement_id=judgement.id,
        supporting_labels=support_labels,
        contradicting_labels=opposing_labels,
        invalid_labels=invalid,
        support_groups=support_groups,
        opposition_groups=opposition_groups,
        support_tier=support_tier,
        opposition_tier=opposition_tier,
        balance=balance,
        status=status,
        confidence_ceiling=ceiling,
        final_confidence=judgement.confidence,
        explanation=tuple(reasons),
        limitations=tuple(limits),
        improvements=tuple(improvements),
    )


def build_report_assessment(
    body: ReportBody,
    evidence: Sequence[EvidenceItem],
    findings: Sequence[Finding],
) -> ReportAssessment:
    """Freeze the final body's assessment after optional advocacy; never invent legacy scores."""
    unique = sorted({item.label: item for item in evidence}.values(), key=lambda item: item.label)
    rows = tuple(
        EvidenceAssessment(
            label=item.label,
            event_id=item.event_id,
            source_id=item.source_id,
            reliability=item.reliability,
            credibility=item.credibility,
            contribution=_tier(item),
            organisation=_organisation(item),
            flags=tuple(sorted(item.flags)),
            reasons=(
                f"Source reliability {item.reliability} and item credibility {item.credibility}: "
                f"{_tier(item).value} contribution under {METHOD_VERSION}.",
            ),
        )
        for item in unique
    )
    judgements = tuple(assess_judgement(judgement, unique) for judgement in body.key_judgements)
    groups = _groups(unique, _group_index(unique))
    return ReportAssessment(
        method_version=METHOD_VERSION,
        evidence=rows,
        judgements=judgements,
        tallies=AssessmentTallies(
            evidence_items=len(rows),
            declared_groups=sum(group.known_organisation for group in groups),
            unknown_provenance_items=sum(row.organisation is None for row in rows),
            possible_copy_groups=sum(group.possible_copy for group in groups),
            judgements=len(judgements),
            strong=sum(row.contribution is Contribution.STRONG for row in rows),
            moderate=sum(row.contribution is Contribution.MODERATE for row in rows),
            limited=sum(row.contribution is Contribution.LIMITED for row in rows),
            unassessed=sum(row.contribution is Contribution.UNASSESSED for row in rows),
            supported_judgements=sum(row.status == "supported" for row in judgements),
            limited_judgements=sum(row.status == "limited" for row in judgements),
            contested_judgements=sum(row.status == "contested" for row in judgements),
            unsupported_judgements=sum(row.status == "unsupported" for row in judgements),
        ),
        validation_errors=sum(finding.severity.value == "error" for finding in findings),
        validation_warnings=sum(finding.severity.value == "warning" for finding in findings),
        limitations=LIMITATIONS,
    )
