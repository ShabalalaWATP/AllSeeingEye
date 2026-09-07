"""Model provenance survives human corrections and cannot be replaced by their author."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.adapters.persistence.claim_payloads import decode_revision, encode_revision
from ase.domain.claim_origin import ClaimModelOrigin
from ase.domain.claim_revisions import ClaimReviewState, revise_claim
from test_claim_revisions import revision_args


def origin(now):
    return ClaimModelOrigin(
        uuid4(),
        uuid4(),
        3,
        "openai_compatible",
        "requested-model",
        "returned-model",
        "a" * 64,
        "ase-claim-proposals-v1",
        now,
    )


def test_origin_roundtrip_and_operator_revision_preserve_initial_provenance():
    args = revision_args()
    initial = revise_claim(**args, model_origin=origin(args["now"]))
    payload, digest, size = encode_revision(initial)
    assert decode_revision(payload, digest, size) == initial
    reviewed = revise_claim(
        **{
            **args,
            "revision_id": uuid4(),
            "previous": initial,
            "state": ClaimReviewState.REVIEWED,
            "reason": "Checked original excerpt.",
        }
    )
    assert reviewed.model_origin == initial.model_origin
    assert initial.state is ClaimReviewState.PROPOSED
    with pytest.raises(ValueError, match="replace"):
        revise_claim(
            **{**args, "revision_id": uuid4(), "previous": initial},
            model_origin=origin(args["now"]),
        )


def test_supported_long_provider_model_ids_survive_storage():
    args = revision_args()
    value = replace(origin(args["now"]), requested_model="a" * 2048, returned_model="b" * 2048)
    revision = revise_claim(**args, model_origin=value)
    payload, digest, size = encode_revision(revision)
    assert decode_revision(payload, digest, size).model_origin == value


@pytest.mark.parametrize("change", ["future", "naive", "digest", "revision", "model"])
def test_malformed_origin_never_reaches_storage(change):
    args = revision_args()
    value = origin(args["now"])
    if change == "future":
        value = replace(value, generated_at=args["now"] + timedelta(seconds=1))
    elif change == "naive":
        value = replace(value, generated_at=args["now"].replace(tzinfo=None))
    elif change == "digest":
        value = replace(value, input_sha256="not a hash")
    elif change == "revision":
        value = replace(value, profile_revision=True)
    else:
        value = replace(value, returned_model="x" * 2049)
    with pytest.raises(ValueError):
        revise_claim(**args, model_origin=value)
    with pytest.raises(ValueError):
        encode_revision(replace(revise_claim(**args), model_origin=value))
