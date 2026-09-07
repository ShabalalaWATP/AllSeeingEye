"""Canonical bounded relationship decisions; hashes detect corruption, not source truth."""

import hashlib
import json
from typing import Any

from pydantic import TypeAdapter

from ase.domain.relationship_review import (
    RelationshipReviewRevision,
    validate_relationship_revision,
)

_ADAPTER = TypeAdapter(RelationshipReviewRevision)
MAX_RELATIONSHIP_REVISION_BYTES = 256 * 1024


def _canonical(payload: dict[str, Any]) -> bytes:
    output = bytearray()
    encoder = json.JSONEncoder(
        sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    try:
        for part in encoder.iterencode(payload):
            encoded = part.encode("utf-8")
            if len(output) + len(encoded) > MAX_RELATIONSHIP_REVISION_BYTES:
                raise ValueError("Relationship revision exceeds storage limit")
            output.extend(encoded)
    except (TypeError, RecursionError) as exc:
        raise ValueError("Invalid relationship revision payload") from exc
    return bytes(output)


def encode_relationship_revision(
    value: RelationshipReviewRevision,
) -> tuple[dict[str, Any], str, int]:
    validate_relationship_revision(value)
    payload = _ADAPTER.dump_python(value, mode="json")
    if not isinstance(payload, dict):
        raise ValueError("Invalid relationship revision payload")
    encoded = _canonical(payload)
    return payload, hashlib.sha256(encoded).hexdigest(), len(encoded)


def decode_relationship_revision(
    payload: dict[str, Any], digest: str, size: int
) -> RelationshipReviewRevision:
    if (
        not isinstance(payload, dict)
        or type(size) is not int
        or not 0 < size <= MAX_RELATIONSHIP_REVISION_BYTES
    ):
        raise ValueError("Invalid relationship revision envelope")
    encoded = _canonical(payload)
    if len(encoded) != size or hashlib.sha256(encoded).hexdigest() != digest:
        raise ValueError("Relationship revision integrity mismatch")
    value = _ADAPTER.validate_python(payload)
    canonical, _, _ = encode_relationship_revision(value)
    # Compare bytes, not Python equality: True == 1 must not permit coercion.
    if _canonical(canonical) != encoded:
        raise ValueError("Relationship revision is not in canonical form")
    return value
