"""Canonical bounded claim storage with integrity checks, not source authentication."""

import hashlib
import json
from typing import Any

from pydantic import TypeAdapter

from ase.domain.claim_revisions import ClaimRevision, validate_claim_revision

_ADAPTER = TypeAdapter(ClaimRevision)
MAX_REVISION_BYTES = 256 * 1024


def encode_revision(value: ClaimRevision) -> tuple[dict[str, Any], str, int]:
    validate_claim_revision(value)
    payload = _ADAPTER.dump_python(value, mode="json")
    if not isinstance(payload, dict):
        raise ValueError("Invalid claim revision payload")
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    if not 0 < len(encoded) <= MAX_REVISION_BYTES:
        raise ValueError("Claim revision exceeds storage limit")
    return payload, hashlib.sha256(encoded).hexdigest(), len(encoded)


def decode_revision(payload: dict[str, Any], digest: str, size: int) -> ClaimRevision:
    value = _ADAPTER.validate_python(payload)
    canonical, actual_digest, actual_size = encode_revision(value)
    if canonical != payload or actual_digest != digest or actual_size != size:
        raise ValueError("Claim revision integrity mismatch")
    return value
