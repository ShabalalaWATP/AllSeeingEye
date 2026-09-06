"""Frozen source ratings retain their policy and unknowns, not the latest registry metadata."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from ase.domain.events import Reliability
from ase.domain.evidence import EvidenceItem
from ase.domain.report_records import evidence_from_list, evidence_to_list
from ase.domain.source_rating_records import source_rating_from_dict, source_rating_to_dict
from ase.domain.source_ratings import source_rating_for, unassessed_source_rating
from feeds_helpers import NOW, make_event


def payload():
    return source_rating_to_dict(source_rating_for("bbc_world", Reliability.B))


def test_frozen_metadata_roundtrip_retains_exact_grade_policy_basis_and_review_date():
    rating = replace(source_rating_for("bbc_world", Reliability.B), reviewed_at=NOW)
    original = EvidenceItem.from_event(
        "E1",
        make_event(),
        NOW,
        source_name="BBC",
        independence_key="BBC",
        source_rating=rating,
    )
    stored = json.loads(json.dumps(evidence_to_list((original,))))
    assert stored[0]["source_rating"]["reviewed_at"] == NOW.isoformat()
    assert evidence_from_list(stored) == (original,)
    frozen = source_rating_from_dict({**payload(), "policy_version": "historic-policy"})
    assert frozen is not None and frozen.policy_version == "historic-policy"
    assert (
        source_rating_from_dict(source_rating_to_dict(unassessed_source_rating()))
        == unassessed_source_rating()
    )


def test_legacy_absent_or_null_metadata_is_not_filled_from_current_source_catalogue():
    event = EvidenceItem.from_event(
        "E1",
        make_event(source_id="bbc_world"),
        NOW,
        source_name="BBC",
        independence_key="BBC",
    )
    row = evidence_to_list((event,))[0]
    assert row["source_rating"] is None
    assert evidence_from_list([row])[0].source_rating is None
    row.pop("source_rating")
    assert evidence_from_list([row])[0].source_rating is None
    assert source_rating_to_dict(None) is None and source_rating_from_dict(None) is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("policy_version", ""),
        ("policy_version", "x" * 65),
        ("basis", " "),
        ("basis", "x" * 1201),
        ("scope", True),
        ("status", "verified"),
        ("assessed_grade", True),
        ("assessed_grade", "AA"),
        ("assessed_grade", None),
        ("limitations", []),
        ("limitations", ["x"] * 17),
        ("limitations", [True]),
        ("limitations", "a limitation"),
        ("provenance_role", "trusted"),
        ("publisher_reliability_assessed", "false"),
        ("publisher_reliability_assessed", 1),
        ("reviewed_at", "2026-09-06"),
        ("reviewed_at", "not-a-date"),
        ("reviewed_at", True),
    ],
)
def test_malformed_source_rating_fields_are_not_coerced_or_silently_truncated(field, value):
    data = deepcopy(payload())
    data[field] = value
    with pytest.raises(ValueError):
        source_rating_from_dict(data)


@pytest.mark.parametrize("data", [[], {}, {"unexpected": "value"}])
def test_unrecognised_metadata_shape_is_rejected(data):
    with pytest.raises(ValueError):
        source_rating_from_dict(data)


def test_unassessed_and_platform_profiles_cannot_claim_publisher_reliability():
    for updates in (
        {"status": "unassessed"},
        {"provenance_role": "aggregator"},
        {"provenance_role": "platform"},
    ):
        with pytest.raises(ValueError):
            source_rating_from_dict({**payload(), **updates})
    with pytest.raises(ValueError):
        source_rating_to_dict(
            replace(unassessed_source_rating(), publisher_reliability_assessed=True)
        )
