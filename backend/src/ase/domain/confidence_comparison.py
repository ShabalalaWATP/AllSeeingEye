"""Explain frozen assessment differences without recalculation or inferred semantic matches."""

import json
from collections import Counter
from dataclasses import asdict
from typing import Any

from ase.domain.annotation_comparison import (
    ComparisonSide,
    ConfidenceChange,
    JudgementCorrespondence,
)


def _judgements(side: ComparisonSide) -> dict[str, str]:
    values = {row.id: row.statement for row in side.judgements}
    if len(values) != len(side.judgements) or len(values) > 20:
        raise ValueError("Judgement IDs must be unique and bounded for explicit comparison")
    return values


def _facts(side: ComparisonSide, judgement_id: str) -> dict[str, Any] | None:
    if side.assessment is None:
        return None
    matches = [row for row in side.assessment.judgements if row.judgement_id == judgement_id]
    if len(matches) != 1:
        return None
    judgement = matches[0]
    evidence = {row.label: (row.source_id, row.event_id) for row in side.evidence}
    if len(evidence) != len(side.evidence):
        raise ValueError("Frozen evidence labels are ambiguous")

    def identities(labels: tuple[str, ...]) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(evidence[label] for label in labels if label in evidence))

    used = set(judgement.supporting_labels) | set(judgement.contradicting_labels)
    group_labels = {
        label
        for group in (*judgement.support_groups, *judgement.opposition_groups)
        for label in group.labels
    }
    if judgement.invalid_labels or not (used | group_labels).issubset(evidence):
        return None
    rows = [row for row in side.assessment.evidence if row.label in used]
    if {row.label for row in rows} != used:
        return None
    if any(evidence.get(row.label) != (row.source_id, row.event_id) for row in rows):
        raise ValueError("Frozen assessment evidence differs from its source/event anchor")
    if len({row.label for row in rows}) != len(rows):
        raise ValueError("Frozen assessment evidence labels are ambiguous")

    def groups(values: Any) -> tuple[str, ...]:
        return tuple(
            sorted(
                json.dumps(
                    {
                        **{
                            key: value
                            for key, value in asdict(row).items()
                            if key not in {"id", "labels"}
                        },
                        "members": identities(row.labels),
                    },
                    sort_keys=True,
                    default=str,
                )
                for row in values
            )
        )

    return {
        "method_version": side.assessment.method_version,
        "supporting_evidence": identities(judgement.supporting_labels),
        "opposing_evidence": identities(judgement.contradicting_labels),
        "reliability": tuple(
            sorted((row.source_id, row.event_id, row.reliability) for row in rows)
        ),
        "information_credibility": tuple(
            sorted((row.source_id, row.event_id, row.credibility) for row in rows)
        ),
        "contribution_tiers": tuple(
            sorted((row.source_id, row.event_id, row.contribution) for row in rows)
        ),
        "source_groups": (groups(judgement.support_groups), groups(judgement.opposition_groups)),
        "balance": judgement.balance,
        "confidence_ceiling": judgement.confidence_ceiling,
        "final_confidence": judgement.final_confidence,
        "explanation": judgement.explanation,
        "limitations": (side.assessment.limitations, judgement.limitations),
    }


def confidence_deltas(
    before: ComparisonSide,
    after: ComparisonSide,
    correspondences: tuple[JudgementCorrespondence, ...],
) -> tuple[ConfidenceChange, ...]:
    old, new = _judgements(before), _judgements(after)
    pairs: dict[str, str] = {}
    declared = set()
    if not isinstance(correspondences, tuple) or len(correspondences) > 20:
        raise ValueError("Judgement correspondence must be a bounded immutable selection")
    for pair in correspondences:
        left, right = pair.before_judgement_id, pair.after_judgement_id
        if (
            left not in old
            or right not in new
            or left in pairs
            or right in pairs.values()
            or not pair.rationale.strip()
            or len(pair.rationale) > 500
        ):
            raise ValueError("Declare one-to-one correspondence between existing judgements")
        pairs[left] = right
        declared.add(left)
    old_counts, new_counts = Counter(old.values()), Counter(new.values())
    for left, statement in old.items():
        matches = [right for right, value in new.items() if value == statement]
        if (
            statement.strip()
            and old_counts[statement] == new_counts[statement] == 1
            and left not in pairs
            and matches[0] not in pairs.values()
        ):
            pairs[left] = matches[0]
    result = []
    for left in old:
        matched_right = pairs.get(left)
        if matched_right is None:
            result.append(
                ConfidenceChange(
                    left,
                    None,
                    "unmatched",
                    "removed",
                    (),
                    (
                        "No judgement correspondence established. "
                        "This remains a separate frozen assessment.",
                    ),
                )
            )
            continue
        fields, explanations = _explain(_facts(before, left), _facts(after, matched_right))
        result.append(
            ConfidenceChange(
                left,
                matched_right,
                "operator_declared" if left in declared else "exact_statement",
                "changed" if fields else "unchanged",
                fields,
                tuple(explanations),
            )
        )
    for right in new:
        if right not in pairs.values():
            result.append(
                ConfidenceChange(
                    None,
                    right,
                    "unmatched",
                    "added",
                    (),
                    (
                        "No judgement correspondence established. "
                        "This remains a separate frozen assessment.",
                    ),
                )
            )
    return tuple(result)


def _explain(
    old: dict[str, Any] | None, new: dict[str, Any] | None
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if old is None or new is None:
        return (
            ("assessment_availability",) if (old is None) != (new is None) else (),
            (
                "A corresponding frozen assessment is unavailable or has incomplete "
                "evidence references; "
                "no confidence direction is inferred.",
            ),
        )
    fields = tuple(key for key in old if old[key] != new[key])
    explanations = []
    for field in fields:
        if field in {"final_confidence", "confidence_ceiling"}:
            explanations.append(
                f"Recorded {field.replace('_', ' ')}: {old[field]} to {new[field]}."
            )
        elif field == "method_version":
            explanations.append(
                "Assessment method versions differ; frozen results were not recomputed."
            )
        else:
            explanations.append(f"Frozen {field.replace('_', ' ')} inputs differ.")
    if not fields:
        explanations.append("No recorded assessment differences for this correspondence.")
    explanations.append(
        "These are observed differences, not a uniquely established cause or truth probability."
    )
    return fields, tuple(explanations)
