"""Stored relationship review rows reject coercion, unknown fields and corrupt metadata."""

import hashlib
import json

import pytest

from ase.adapters.persistence.relationship_payloads import (
    decode_relationship_revision,
    encode_relationship_revision,
)
from ase.domain.relationship_review import revise_relationship_review
from test_relationship_review import arguments


def test_exact_roundtrip_and_stable_digest():
    revision = revise_relationship_review(**arguments())
    payload, digest, size = encode_relationship_revision(revision)
    assert decode_relationship_revision(payload, digest, size) == revision
    assert encode_relationship_revision(revision) == (payload, digest, size)
    assert payload["assertion"]["attributes"][2]["value"] == "reported_accounting_consolidation"


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
    payload, _, _ = encode_relationship_revision(revise_relationship_review(**arguments()))
    payload[field] = value
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    with pytest.raises(ValueError):
        decode_relationship_revision(payload, hashlib.sha256(encoded).hexdigest(), len(encoded))


@pytest.mark.parametrize("field", ["payload", "digest", "size", "boolean_size"])
def test_corrupt_envelope_is_rejected(field):
    payload, digest, size = encode_relationship_revision(revise_relationship_review(**arguments()))
    if field == "payload":
        payload["rationale"] = "Replaced"
    elif field == "digest":
        digest = "0" * 64
    elif field == "size":
        size += 1
    else:
        size = True
    with pytest.raises(ValueError):
        decode_relationship_revision(payload, digest, size)
