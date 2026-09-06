"""Immutable bounded provenance hints, retained as untrusted data rather than HTML or links."""

import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any

from ase.domain.events import MAX_ATTRIBUTE_CHARS, MAX_ATTRIBUTES, JsonScalar

MAX_ATTRIBUTE_KEY_CHARS = 64
MAX_EXACT_INTEGER = 2**53 - 1


@dataclass(frozen=True, slots=True)
class EvidenceAttribute:
    key: str
    value: JsonScalar


def _valid_key(key: object) -> bool:
    return isinstance(key, str) and bool(key.strip()) and len(key) <= MAX_ATTRIBUTE_KEY_CHARS


def _valid_scalar(value: object) -> bool:
    if value is None or type(value) is bool:
        return True
    if isinstance(value, str):
        return len(value) <= MAX_ATTRIBUTE_CHARS
    if type(value) is int:
        return abs(value) <= MAX_EXACT_INTEGER
    return type(value) is float and math.isfinite(value)


def freeze_evidence_attributes(
    attributes: Mapping[str, JsonScalar],
) -> tuple[EvidenceAttribute, ...]:
    """Retain supplied scalar hints, without guessing their authenticity or attribution."""
    retained: list[EvidenceAttribute] = []
    for key, value in attributes.items():
        if not _valid_key(key):
            continue
        bounded = value[:MAX_ATTRIBUTE_CHARS] if isinstance(value, str) else value
        if not _valid_scalar(bounded):
            continue
        retained.append(EvidenceAttribute(key, bounded))
        if len(retained) >= MAX_ATTRIBUTES:
            break
    return tuple(retained)


def evidence_attributes_from_list(data: object) -> tuple[EvidenceAttribute, ...]:
    if data is None:
        return ()
    if not isinstance(data, list) or len(data) > MAX_ATTRIBUTES:
        raise ValueError("Frozen evidence attributes must be a bounded list")
    rows: list[EvidenceAttribute] = []
    seen: set[str] = set()
    for row in data:
        if not isinstance(row, dict) or set(row) != {"key", "value"}:
            raise ValueError("Frozen evidence attribute must contain key and value")
        key, value = row["key"], row["value"]
        if not _valid_key(key) or key in seen or not _valid_scalar(value):
            raise ValueError("Frozen evidence attribute has an invalid key or scalar value")
        seen.add(key)
        rows.append(EvidenceAttribute(key, value))
    return tuple(rows)


def evidence_attributes_to_list(attributes: Sequence[EvidenceAttribute]) -> list[dict[str, Any]]:
    data = [asdict(attribute) for attribute in attributes]
    evidence_attributes_from_list(data)
    return data
