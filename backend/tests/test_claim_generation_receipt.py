"""Automatic claim outcomes are explicit and preserve exact initial revision identity."""

from dataclasses import replace
from uuid import uuid4

import pytest

from ase.domain.claim_generation import (
    ClaimGenerationReceipt,
    ClaimGenerationStatus,
    claim_generation_from_dict,
    claim_generation_to_dict,
)
from feeds_helpers import NOW
from test_claim_origin import origin


@pytest.mark.parametrize("status", list(ClaimGenerationStatus))
def test_receipt_roundtrip_keeps_outcomes_distinct(status):
    receipt = ClaimGenerationReceipt(status)
    if status is ClaimGenerationStatus.COMPLETED:
        receipt = replace(receipt, revision_ids=(uuid4(), uuid4()), model_origin=origin(NOW))
    assert claim_generation_from_dict(claim_generation_to_dict(receipt)) == receipt


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "oversize", "false_success", "version", "origin"]
)
def test_invalid_receipt_is_never_serialised(change):
    receipt = ClaimGenerationReceipt(ClaimGenerationStatus.COMPLETED, (uuid4(),), origin(NOW))
    if change == "missing":
        receipt = replace(receipt, model_origin=None)
    elif change == "duplicate":
        receipt = replace(receipt, revision_ids=receipt.revision_ids * 2)
    elif change == "oversize":
        receipt = replace(receipt, revision_ids=tuple(uuid4() for _ in range(21)))
    elif change == "false_success":
        receipt = replace(receipt, status=ClaimGenerationStatus.EMPTY)
    elif change == "version":
        receipt = replace(receipt, schema_version=True)
    else:
        receipt = replace(receipt, status=ClaimGenerationStatus.NO_MODEL, revision_ids=())
    with pytest.raises(ValueError):
        claim_generation_to_dict(receipt)


def test_receipt_rejects_extra_private_payload_and_unknown_schema():
    value = claim_generation_to_dict(ClaimGenerationReceipt(ClaimGenerationStatus.EMPTY))
    with pytest.raises(ValueError):
        claim_generation_from_dict({**value, "prompt": "private text"})
    with pytest.raises(ValueError):
        claim_generation_from_dict({**value, "schema_version": 2})
