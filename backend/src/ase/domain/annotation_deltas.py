"""Same-root or explicitly declared comparisons, without fuzzy annotation matching."""

import json
from dataclasses import asdict
from typing import Any
from uuid import UUID

from ase.domain.annotation_comparison import (
    AnnotationChange,
    AnnotationCorrespondence,
    AnnotationKind,
    ChangeStatus,
    ComparisonEvidenceChange,
    ComparisonSide,
)
from ase.domain.claim_revisions import ClaimCitation, ClaimRevision
from ase.domain.identity_review import IdentityDecisionRevision
from ase.domain.relationship_review import RelationshipReviewRevision

Revision = ClaimRevision | IdentityDecisionRevision | RelationshipReviewRevision


def annotation_rows(side: ComparisonSide) -> dict[tuple[AnnotationKind, UUID], Revision]:
    values: dict[tuple[AnnotationKind, UUID], Revision] = {}
    for kind, rows in (
        ("claim", side.revisions),
        ("identity", side.identity_revisions),
        ("relationship", side.relationship_revisions),
    ):
        for row in rows:
            key: tuple[AnnotationKind, UUID] = (kind, row.id)  # type: ignore[assignment]
            if key in values:
                raise ValueError("Select each annotation revision once")
            values[key] = row
    if len(values) > 20:
        raise ValueError("Select at most twenty annotation revisions per side")
    roots = [(kind, root_id(row)) for (kind, _), row in values.items()]
    if len(set(roots)) != len(roots):
        raise ValueError("Select only one revision of each annotation root per side")
    return values


def root_id(row: Revision) -> UUID:
    if isinstance(row, ClaimRevision):
        return row.claim_id
    if isinstance(row, IdentityDecisionRevision):
        return row.decision_id
    return row.relationship_id


def _citations(values: tuple[ClaimCitation, ...], side: ComparisonSide) -> tuple[str, ...]:
    # Labels are local to a version. Source/event identity and the literal locator persist.
    return tuple(
        sorted(
            json.dumps(
                {
                    **{key: value for key, value in asdict(row).items() if key != "label"},
                    "source_id": next(
                        item.source_id for item in side.evidence if item.label == row.label
                    ),
                },
                sort_keys=True,
                default=str,
            )
            for row in values
        )
    )


def _content(row: Revision, side: ComparisonSide) -> dict[str, Any]:
    result: dict[str, Any] = {
        "citations": _citations(row.citations, side),
        "unresolved_conflicts": row.unresolved_conflicts,
    }
    if isinstance(row, ClaimRevision):
        result.update(statement=row.statement, kind=row.kind, state=row.state, reason=row.reason)
    else:
        snapshot = row.candidate if isinstance(row, IdentityDecisionRevision) else row.assertion
        substantive = asdict(snapshot)
        for key in (
            "event_id",
            "source_id",
            "source_content_hash",
            "evidence_label",
            "captured_at",
            "published_at",
        ):
            substantive.pop(key, None)
        if isinstance(row, IdentityDecisionRevision):
            substantive["candidate"].pop("evidence_label", None)
            result.update(subject=row.subject, candidate=substantive)
            label = row.candidate.candidate.evidence_label
        else:
            result["assertion"] = substantive
            label = row.assertion.evidence_label
        item = next(item for item in side.evidence if item.label == label)
        result.update(
            disposition=row.disposition,
            rationale=row.rationale,
            source_record=(snapshot.source_id, snapshot.event_id, snapshot.source_content_hash),
            capture_provenance=(label, item.captured_at, item.published_at, item.observed_at),
        )
    return result


def _status(before: object, after: object, fields: tuple[str, ...]) -> ChangeStatus:
    return (
        "added"
        if before is None
        else "removed"
        if after is None
        else "changed"
        if fields
        else "unchanged"
    )


def annotation_deltas(
    before: ComparisonSide,
    after: ComparisonSide,
    correspondences: tuple[AnnotationCorrespondence, ...],
) -> tuple[AnnotationChange, ...]:
    old, new = annotation_rows(before), annotation_rows(after)
    pairs: dict[tuple[AnnotationKind, UUID], tuple[AnnotationKind, UUID]] = {}
    declared = set()
    for key, row in old.items():
        matches = [
            other
            for other, value in new.items()
            if other[0] == key[0] and root_id(row) == root_id(value)
        ]
        if matches:
            pairs[key] = matches[0]
    if not isinstance(correspondences, tuple) or len(correspondences) > 20:
        raise ValueError("Correspondences must be a bounded immutable selection")
    for pair in correspondences:
        left, right = (pair.kind, pair.before_revision_id), (pair.kind, pair.after_revision_id)
        if (
            left not in old
            or right not in new
            or left in pairs
            or right in pairs.values()
            or not pair.rationale.strip()
            or len(pair.rationale) > 500
        ):
            raise ValueError("Declare one-to-one selected same-kind correspondence only")
        pairs[left] = right
        declared.add(left)
    result = []
    for key, row in old.items():
        counterpart = new.get(pairs[key]) if key in pairs else None
        fields = tuple(
            name
            for name, value in _content(row, before).items()
            if counterpart is not None and value != _content(counterpart, after)[name]
        )
        result.append(
            AnnotationChange(
                key[0],
                row.id,
                counterpart.id if counterpart else None,
                "operator_declared"
                if key in declared
                else "same_root"
                if counterpart
                else "unmatched",
                _status(row, counterpart, fields),
                fields,
            )
        )
    for key, row in new.items():
        if key not in pairs.values():
            result.append(AnnotationChange(key[0], None, row.id, "unmatched", "added", ()))
    return tuple(result)


def evidence_deltas(
    before: ComparisonSide, after: ComparisonSide
) -> tuple[ComparisonEvidenceChange, ...]:
    def index(side: ComparisonSide) -> dict[tuple[str, str], Any]:
        values = {(row.source_id, row.event_id): row for row in side.evidence}
        if len(values) != len(side.evidence) or len(values) > 1000:
            raise ValueError("Frozen evidence identities must be unique and bounded")
        if len({row.label for row in side.evidence}) != len(side.evidence):
            raise ValueError("Frozen evidence labels must be unique")
        return values

    old, new = index(before), index(after)
    result = []
    for source, event in sorted(old.keys() | new.keys()):
        left, right = old.get((source, event)), new.get((source, event))
        fields = (
            tuple(
                key
                for key, value in asdict(left).items()
                if key != "label" and value != asdict(right)[key]
            )
            if left and right
            else ()
        )
        result.append(
            ComparisonEvidenceChange(
                source,
                event,
                left.label if left else None,
                right.label if right else None,
                _status(left, right, fields),
                fields,
            )
        )
    return tuple(result)
