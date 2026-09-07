"""Storage validates structure even when a malformed payload has a matching hash."""

import hashlib
import json
from dataclasses import replace

import pytest
from pydantic import TypeAdapter

from ase.adapters.persistence.claim_payloads import decode_revision, encode_revision
from ase.domain.claim_revisions import ClaimRevision, revise_claim
from test_claim_revisions import revision_args


@pytest.mark.parametrize("bad", ["blank", "long", "empty", "conflicts", "offset", "time"])
def test_invalid_revisions_rejected_on_both_storage_paths(bad):
    value = revise_claim(**revision_args())
    if bad == "blank":
        value = replace(value, statement=" ")
    elif bad == "long":
        value = replace(value, statement="x" * 1201)
    elif bad == "empty":
        value = replace(value, citations=())
    elif bad == "conflicts":
        value = replace(value, unresolved_conflicts=("x",) * 21)
    elif bad == "time":
        value = replace(value, created_at=value.created_at.replace(tzinfo=None))
    else:
        citation = value.citations[0]
        value = replace(
            value, citations=(replace(citation, excerpt=replace(citation.excerpt, start=-1)),)
        )
    with pytest.raises(ValueError):
        encode_revision(value)
    payload = TypeAdapter(ClaimRevision).dump_python(value, mode="json")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    with pytest.raises(ValueError):
        decode_revision(payload, hashlib.sha256(encoded).hexdigest(), len(encoded))
