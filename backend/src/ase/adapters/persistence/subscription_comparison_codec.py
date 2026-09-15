"""Strict JSON codec for immutable subscription comparison rows."""

from typing import cast

from ase.adapters.persistence.subscription_edition_models import (
    SubscriptionEditionComparisonRow,
)
from ase.domain.research_changes import (
    ChangeClassification,
    ComparisonReason,
    ComparisonState,
)
from ase.domain.subscription_comparisons import EditionComparison

_FIELDS = (
    "reasons",
    "changed_claim_ids",
    "corrected_evidence_ids",
    "novel_evidence_ids",
    "syndicated_duplicate_ids",
)


def comparison_values(value: EditionComparison) -> dict[str, object]:
    result = value.result
    return {
        "edition_id": value.edition_id,
        "previous_version_id": value.previous_version_id,
        "current_version_id": value.current_version_id,
        "state": result.state.value,
        "result": {
            "reasons": [reason.value for reason in result.reasons],
            "changed_claim_ids": list(result.changed_claim_ids),
            "corrected_evidence_ids": list(result.corrected_evidence_ids),
            "novel_evidence_ids": list(result.novel_evidence_ids),
            "syndicated_duplicate_ids": list(result.syndicated_duplicate_ids),
        },
        "created_at": value.created_at,
    }


def comparison_from_row(row: SubscriptionEditionComparisonRow) -> EditionComparison:
    value = row.result
    if not isinstance(value, dict) or set(value) != set(_FIELDS):
        raise ValueError("Invalid saved subscription comparison.")
    lists = {key: value[key] for key in _FIELDS}
    if any(
        not isinstance(items, list)
        or len(items) > 1000
        or any(not isinstance(item, str) or len(item) > 300 for item in items)
        for items in lists.values()
    ):
        raise ValueError("Saved subscription comparison exceeds its bounds.")
    typed = {key: cast(list[str], lists[key]) for key in _FIELDS}
    result = ChangeClassification(
        state=ComparisonState(row.state),
        reasons=tuple(ComparisonReason(item) for item in typed["reasons"]),
        changed_claim_ids=tuple(typed["changed_claim_ids"]),
        corrected_evidence_ids=tuple(typed["corrected_evidence_ids"]),
        novel_evidence_ids=tuple(typed["novel_evidence_ids"]),
        syndicated_duplicate_ids=tuple(typed["syndicated_duplicate_ids"]),
    )
    return EditionComparison(
        row.edition_id,
        row.previous_version_id,
        row.current_version_id,
        result,
        row.created_at,
    )
