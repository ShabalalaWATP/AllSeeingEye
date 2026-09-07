"""Exact captured GLEIF assertions, never inferred ownership or current validity."""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast

from ase.domain.evidence_attributes import EvidenceAttribute, evidence_attributes_to_list
from ase.domain.report_records import ReportVersion

RELATIONSHIP_SOURCES = {
    "research-gleif-direct-parent": ("direct", "IS_DIRECTLY_CONSOLIDATED_BY"),
    "research-gleif-ultimate-parent": ("ultimate", "IS_ULTIMATELY_CONSOLIDATED_BY"),
}


@dataclass(frozen=True, slots=True)
class RelationshipPeriod:
    type: str
    startDate: str  # noqa: N815 - preserve the captured GLEIF period field name
    endDate: str  # noqa: N815 - preserve the captured GLEIF period field name


@dataclass(frozen=True, slots=True)
class RelationshipAssertionSnapshot:
    evidence_label: str
    event_id: str
    source_id: str
    source_content_hash: str
    child_lei: str
    parent_lei: str
    kind: Literal["direct", "ultimate"]
    relationship_type: str
    attributes: tuple[EvidenceAttribute, ...]
    periods: tuple[RelationshipPeriod, ...] | None
    periods_state: Literal["parsed", "missing", "unavailable"]
    captured_at: datetime
    published_at: datetime | None


def _periods(raw: object) -> tuple[tuple[RelationshipPeriod, ...] | None, str]:
    if raw is None:
        return None, "missing"
    if not isinstance(raw, str) or len(raw) > 500:
        return None, "unavailable"

    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        values = dict(pairs)
        if len(values) != len(pairs):
            raise ValueError("Duplicate period fields")
        return values

    try:
        values = json.loads(raw, object_pairs_hook=unique)
        if not isinstance(values, list) or len(values) > 20:
            raise ValueError("Invalid captured periods")
        result = []
        for value in values:
            if (
                not isinstance(value, dict)
                or set(value) != {"type", "startDate", "endDate"}
                or any(not isinstance(item, str) or len(item) > 50 for item in value.values())
            ):
                raise ValueError("Invalid captured period")
            result.append(RelationshipPeriod(**value))
        return tuple(result), "parsed"
    except (ValueError, TypeError, RecursionError):
        return None, "unavailable"


def validate_relationship_assertion(value: RelationshipAssertionSnapshot) -> None:
    if not isinstance(value, RelationshipAssertionSnapshot):
        raise ValueError("Invalid relationship assertion")
    for text, limit in (
        (value.evidence_label, 64),
        (value.event_id, 500),
        (value.source_id, 500),
        (value.source_content_hash, 500),
    ):
        if not isinstance(text, str) or not text.strip() or len(text) > limit:
            raise ValueError("Invalid relationship evidence anchor")
    if not isinstance(value.attributes, tuple):
        raise ValueError("Relationship attributes must be immutable")
    evidence_attributes_to_list(value.attributes)
    attributes = {row.key: row.value for row in value.attributes}
    if len(attributes) != len(value.attributes):
        raise ValueError("Duplicate relationship attributes")
    expected = RELATIONSHIP_SOURCES.get(value.source_id)
    if (
        expected is None
        or (value.kind, value.relationship_type) != expected
        or attributes.get("record_kind") != "reported_accounting_consolidation"
        or attributes.get("reported_relationship_type") != value.relationship_type
        or attributes.get("child_lei") != value.child_lei
        or attributes.get("parent_lei") != value.parent_lei
    ):
        raise ValueError("Unsupported or inconsistent captured relationship")
    for lei in (value.child_lei, value.parent_lei):
        if not isinstance(lei, str) or re.fullmatch(r"[A-Z0-9]{18}[0-9]{2}", lei) is None:
            raise ValueError("Invalid captured relationship LEI")
    if (value.periods, value.periods_state) != _periods(attributes.get("reported_periods")):
        raise ValueError("Relationship periods differ from captured evidence")
    for date in (value.captured_at, value.published_at):
        if date is not None and (not isinstance(date, datetime) or date.utcoffset() is None):
            raise ValueError("Invalid relationship evidence timestamp")
    if value.captured_at is None:
        raise ValueError("Relationship evidence requires its capture timestamp")


def freeze_relationship_assertion(
    version: ReportVersion, label: str
) -> RelationshipAssertionSnapshot:
    items = [item for item in version.evidence if item.label == label]
    if len(items) != 1 or items[0].source_id not in RELATIONSHIP_SOURCES:
        raise ValueError("Choose one supported captured relationship assertion")
    item = items[0]
    attributes = {row.key: row.value for row in item.attributes}
    kind, relationship_type = RELATIONSHIP_SOURCES[item.source_id]
    periods, state = _periods(attributes.get("reported_periods"))
    value = RelationshipAssertionSnapshot(
        item.label,
        item.event_id,
        item.source_id,
        item.content_hash,
        cast(str, attributes.get("child_lei")),
        cast(str, attributes.get("parent_lei")),
        cast(Literal["direct", "ultimate"], kind),
        relationship_type,
        item.attributes,
        periods,
        cast(Literal["parsed", "missing", "unavailable"], state),
        item.captured_at,
        item.published_at,
    )
    validate_relationship_assertion(value)
    return value
