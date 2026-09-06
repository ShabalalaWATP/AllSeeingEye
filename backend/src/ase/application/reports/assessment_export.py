"""Shared plain-text projection of a saved automated assessment for every export."""

from collections.abc import Sequence

from ase.domain.evidence_matrix import ContributionGroup, ReportAssessment

BALANCE_LABELS = {
    "no_support": "No cited support",
    "support_only": "Support cited, no opposition assigned to this judgement",
    "support_stronger": "Supporting contribution is stronger",
    "opposition_at_least_as_strong": "Opposing contribution is at least as strong",
}
STATUS_LABELS = {
    "supported": "Supported under the application policy",
    "limited": "Limited support",
    "contested": "Contested support",
    "unsupported": "No assessed support",
}


def _groups(groups: Sequence[ContributionGroup]) -> str:
    return (
        "; ".join(
            f"{group.id}: {', '.join(group.labels)} ({group.contribution}; "
            f"known-origin contribution {group.corroborating_contribution}; "
            f"possible copy {'yes' if group.possible_copy else 'no'}; "
            f"declared organisation {'known' if group.known_organisation else 'unknown'})"
            for group in groups
        )
        or "None"
    )


def assessment_sections(
    assessment: ReportAssessment | None,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Read the frozen result only, including its original method version and caveats."""
    if assessment is None:
        return (
            (
                "Automated evidence assessment",
                ("Unavailable: no automated assessment was saved with this legacy version.",),
            ),
        )
    totals = assessment.tallies
    sections = [
        (
            "Automated evidence assessment",
            (
                f"Method: {assessment.method_version}. "
                "ASE implementation policy informed by doctrine.",
                "Evidence strength is separate from probability and analytical confidence. "
                "It is not an accuracy percentage and does not verify "
                "that citations support the claims.",
                f"Judgements: {totals.judgements}; supported {totals.supported_judgements}, "
                f"limited {totals.limited_judgements}, contested {totals.contested_judgements}, "
                f"no assessed support {totals.unsupported_judgements}.",
                f"Source contributions: strong {totals.strong}, moderate {totals.moderate}, "
                f"limited {totals.limited}, unassessed {totals.unassessed}.",
                "Unassessed means insufficient grading information, not false information.",
                f"Frozen evidence: {totals.evidence_items} item(s); "
                f"{totals.declared_groups} declared organisation group(s); "
                f"{totals.unknown_provenance_items} item(s) with unknown provenance; "
                f"{totals.possible_copy_groups} possible-copy group(s). "
                "Independent sourcing unverified.",
                f"Automated validation: {assessment.validation_errors} error(s), "
                f"{assessment.validation_warnings} warning(s).",
                *(f"Limitation: {text}" for text in assessment.limitations),
            ),
        )
    ]
    for judgement in assessment.judgements:
        sections.append(
            (
                f"{judgement.judgement_id}: automated evidence assessment",
                (
                    f"Supporting evidence strength: {judgement.support_tier}. "
                    f"Opposing evidence strength: {judgement.opposition_tier}. "
                    f"Balance: {BALANCE_LABELS[judgement.balance]}.",
                    f"Judgement support status: {STATUS_LABELS[judgement.status]}.",
                    f"Confidence ceiling: {judgement.confidence_ceiling}; "
                    f"final analytical confidence: {judgement.final_confidence}.",
                    f"Key judgement support groups (model-assigned): "
                    f"{_groups(judgement.support_groups)}.",
                    f"Key judgement opposition groups (model-assigned): "
                    f"{_groups(judgement.opposition_groups)}.",
                    f"Unresolved labels: {', '.join(judgement.invalid_labels) or 'None'}.",
                    *judgement.explanation,
                    *(
                        f"Limitation: {text}"
                        for text in judgement.limitations
                        if text not in assessment.limitations
                    ),
                    *(f"Improve: {text}" for text in judgement.improvements),
                ),
            )
        )
    if assessment.evidence:
        sections.append(
            (
                "Frozen source contribution policy",
                tuple(
                    f"{item.label}: {item.reliability}{item.credibility}; "
                    f"contribution {item.contribution}. {'; '.join(item.reasons)}"
                    for item in assessment.evidence
                ),
            )
        )
    return tuple(sections)
