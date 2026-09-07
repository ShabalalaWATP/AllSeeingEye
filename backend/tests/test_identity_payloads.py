"""Stored identity review rows reject coercion, unknown fields and corrupt metadata."""

import hashlib
import json

import pytest

from ase.adapters.persistence.identity_payloads import (
    decode_identity_revision,
    encode_identity_revision,
)
from ase.domain.identity_review import revise_identity_decision
from test_identity_review import arguments


def test_exact_roundtrip_and_stable_digest():
    revision = revise_identity_decision(**arguments())
    payload, digest, size = encode_identity_revision(revision)
    assert decode_identity_revision(payload, digest, size) == revision
    assert encode_identity_revision(revision) == (payload, digest, size)
    assert payload["candidate"]["attributes"][2]["value"] == "000123"


@pytest.mark.parametrize(
    "field,value",
    [
        ("number", True),
        ("number", "1"),
        ("unknown", "extra"),
        ("rationale", None),
        ("disposition", "verified"),
    ],
)
def test_structural_changes_fail_even_with_recomputed_hash(field, value):
    payload, _, _ = encode_identity_revision(revise_identity_decision(**arguments()))
    payload[field] = value
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    with pytest.raises(ValueError):
        decode_identity_revision(payload, hashlib.sha256(encoded).hexdigest(), len(encoded))


@pytest.mark.parametrize("field", ["payload", "digest", "size", "boolean_size"])
def test_corrupt_envelope_is_rejected(field):
    payload, digest, size = encode_identity_revision(revise_identity_decision(**arguments()))
    if field == "payload":
        payload["rationale"] = "Replaced"
    elif field == "digest":
        digest = "0" * 64
    elif field == "size":
        size += 1
    else:
        size = True
    with pytest.raises(ValueError):
        decode_identity_revision(payload, digest, size)
