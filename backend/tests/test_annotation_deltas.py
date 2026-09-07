"""Exact roots, declared correspondence, source collisions and provenance-only differences."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from annotation_comparison_helpers import side
from ase.domain.annotation_comparison import AnnotationCorrespondence
from ase.domain.annotation_deltas import annotation_deltas, evidence_deltas
from ase.domain.claim_revisions import ClaimReviewState, revise_claim
from ase.domain.relationship_review import revise_relationship_review
from test_claim_revisions import revision_args
from test_relationship_review import arguments


def test_same_root_withdrawal_keeps_exact_predecessor_and_distinct_change_fields():
    args = revision_args()
    first = revise_claim(**args)
    second = revise_claim(
        **{
            **args,
            "revision_id": uuid4(),
            "previous": first,
            "state": ClaimReviewState.WITHDRAWN,
            "reason": "Operator withdrew this assessment.",
        }
    )
    (delta,) = annotation_deltas(
        side(args["version"], claims=(first,)), side(args["version"], claims=(second,)), ()
    )
    assert delta.correspondence == "same_root" and delta.status == "changed"
    assert set(delta.changed_fields) == {"state", "reason"}
    assert (delta.before_revision_id, delta.after_revision_id) == (first.id, second.id)


def test_different_roots_never_match_without_explicit_one_to_one_correspondence():
    args = revision_args()
    first = revise_claim(**args)
    second = revise_claim(**{**args, "revision_id": uuid4(), "claim_id": uuid4()})
    before, after = side(args["version"], claims=(first,)), side(args["version"], claims=(second,))
    assert [row.status for row in annotation_deltas(before, after, ())] == ["removed", "added"]
    pair = AnnotationCorrespondence(
        "claim", first.id, second.id, "Operator compares these assertions."
    )
    (delta,) = annotation_deltas(before, after, (pair,))
    assert delta.status == "unchanged" and delta.correspondence == "operator_declared"
    for invalid in (
        (pair, pair),
        (replace(pair, kind="identity"),),
        (replace(pair, after_revision_id=uuid4()),),
    ):
        with pytest.raises(ValueError):
            annotation_deltas(before, after, invalid)


def test_multiple_revisions_of_one_root_and_override_of_automatic_match_are_rejected():
    args = revision_args()
    first = revise_claim(**args)
    second = revise_claim(**{**args, "revision_id": uuid4(), "previous": first})
    with pytest.raises(ValueError, match="one revision"):
        annotation_deltas(side(args["version"], claims=(first, second)), side(args["version"]), ())
    with pytest.raises(ValueError, match="one-to-one"):
        annotation_deltas(
            side(args["version"], claims=(first,)),
            side(args["version"], claims=(second,)),
            (AnnotationCorrespondence("claim", first.id, second.id, "Explicit"),),
        )


def test_citation_relabelling_is_ignored_but_cross_source_event_collision_is_not():
    args = revision_args()
    first = revise_claim(**args)
    version = args["version"]
    item = replace(version.evidence[0], label="R7")
    revised = replace(version, id=uuid4(), evidence=(item,))
    second = revise_claim(
        **{
            **args,
            "version": revised,
            "revision_id": uuid4(),
            "claim_id": uuid4(),
            "citations": (replace(args["citations"][0], label="R7"),),
        }
    )
    pair = AnnotationCorrespondence("claim", first.id, second.id, "Same captured source text")
    before, after = side(version, claims=(first,)), side(revised, claims=(second,))
    assert "citations" not in annotation_deltas(before, after, (pair,))[0].changed_fields
    collision = replace(after, evidence=(replace(item, source_id="another-source"),))
    assert "citations" in annotation_deltas(before, collision, (pair,))[0].changed_fields
    assert {row.status for row in evidence_deltas(before, collision)} == {"added", "removed"}


def test_relabelled_recaptured_relationship_is_provenance_only():
    args = arguments()
    first = revise_relationship_review(**args)
    version = args["version"]
    item = replace(
        version.evidence[0], label="R7", captured_at=version.created_at + timedelta(days=1)
    )
    newer = replace(version, id=uuid4(), evidence=(item,))
    second = revise_relationship_review(
        **{
            **args,
            "version": newer,
            "revision_id": uuid4(),
            "relationship_id": uuid4(),
            "evidence_label": "R7",
        }
    )
    pair = AnnotationCorrespondence(
        "relationship", first.id, second.id, "Compare the dated assertions"
    )
    before, after = side(version, relationships=(first,)), side(newer, relationships=(second,))
    (delta,) = annotation_deltas(before, after, (pair,))
    assert delta.changed_fields == ("capture_provenance",)
    assert after.relationship_revisions[0].assertion.captured_at == item.captured_at


@pytest.mark.parametrize(
    "key,value",
    [
        ("parent_lei", "5493001KJTIIGC8Y1R12"),
        ("reported_valid_from", "2022-01-01"),
        ("reported_relationship_status", "INACTIVE"),
    ],
)
def test_actual_parent_record_date_or_source_status_change_is_substantive(key, value):
    args = arguments()
    first = revise_relationship_review(**args)
    version = args["version"]
    item = replace(
        version.evidence[0],
        attributes=tuple(
            replace(row, value=value) if row.key == key else row
            for row in version.evidence[0].attributes
        ),
    )
    newer = replace(version, id=uuid4(), evidence=(item,))
    second = revise_relationship_review(
        **{**args, "version": newer, "revision_id": uuid4(), "relationship_id": uuid4()}
    )
    pair = AnnotationCorrespondence("relationship", first.id, second.id, "Compare reported facts")
    (delta,) = annotation_deltas(
        side(version, relationships=(first,)), side(newer, relationships=(second,)), (pair,)
    )
    assert "assertion" in delta.changed_fields
