"""Strict frozen JSON rejects altered derived groups and malformed assessment metadata."""

import copy
import json

import pytest

from ase.application.reports.source_assessment_projection import (
    restore_source_assessment_projection,
)
from ase.domain.source_assessment_records import (
    SourceAssessmentSnapshotError,
    source_assessment_report_from_dict,
    source_assessment_report_to_dict,
)
from source_projection_helpers import BODY, EVIDENCE, VERSION, projection


def test_frozen_projection_round_trips_without_live_rating_resolution():
    original = projection()
    saved = json.loads(json.dumps(source_assessment_report_to_dict(original)))
    restored = source_assessment_report_from_dict(saved, required=True)
    assert restored == original
    assert (
        restore_source_assessment_projection(
            saved, report_version_id=VERSION, body=BODY, evidence=EVIDENCE
        )
        == original
    )


def test_detached_json_and_later_projection_do_not_mutate_the_historical_record():
    original = projection()
    before = source_assessment_report_to_dict(original)
    detached = source_assessment_report_to_dict(original)
    detached["assessments"][0]["reliability"] = "E"
    detached["origins"]["groups"][0]["member_ids"].append("invented")
    projection(rated=False)
    assert source_assessment_report_to_dict(original) == before
    assert source_assessment_report_from_dict(before) == original


@pytest.mark.parametrize(
    "path,value",
    [
        (("schema_version",), True),
        (("schema_version",), 2),
        (("policy_version",), "future"),
        (("report_version_id",), "invalid"),
        (("frozen_at",), "2026-09-14T12:00:00"),
        (("assessments", 0, "credibility"), True),
        (("assessments", 0, "credibility"), 1.0),
        (("assessments", 0, "reliability"), "G"),
        (("assessments", 0, "source_id"), "other"),
        (("assessments", 0, "subject"), "other"),
        (("assessments", 0, "evidence_id"), "E1"),
        (("assessments", 0, "source_revision", "review", "assessor"), "model"),
        (
            ("assessments", 0, "source_revision", "review", "recorded_at"),
            "2027-01-01T00:00:00+00:00",
        ),
        (("origins", "policy_version"), "future"),
        (("origins", "groups", 0, "review_required"), False),
        (("origins", "groups", 0, "known_original_ids"), ["invented"]),
        (("origins", "nodes", 0, "source_id"), "other"),
        (("claims", 0, "uses", 0, "roles"), ["supporting", "supporting"]),
        (("claims", 0, "uses", 0, "roles"), ["context"]),
        (("claims", 0, "uses", 0, "capture_id"), "invented"),
    ],
)
def test_malformed_or_relabelled_saved_records_are_rejected_without_echoing_values(path, value):
    saved = source_assessment_report_to_dict(projection())
    target = saved
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(SourceAssessmentSnapshotError) as error:
        source_assessment_report_from_dict(saved, required=True)
    assert str(error.value) == "Invalid or missing frozen source assessment."


@pytest.mark.parametrize("change", ["extra", "missing", "duplicate", "partial", "wrong_type"])
def test_saved_collection_contract_does_not_drop_unknown_or_missing_records(change):
    saved = source_assessment_report_to_dict(projection())
    if change == "extra":
        saved["unrecognised"] = "value"
    elif change == "missing":
        del saved["claims"]
    elif change == "duplicate":
        saved["assessments"].append(copy.deepcopy(saved["assessments"][0]))
    elif change == "partial":
        saved["assessments"] = []
    else:
        saved["evidence"] = tuple(saved["evidence"])
    with pytest.raises(SourceAssessmentSnapshotError):
        source_assessment_report_from_dict(saved)


@pytest.mark.parametrize(
    "value", [False, [], {"unexpected": "data"}, {"schema_version": 1}, float("nan")]
)
def test_present_invalid_metadata_never_becomes_an_absent_legacy_assessment(value):
    with pytest.raises(SourceAssessmentSnapshotError):
        source_assessment_report_from_dict(value)


def test_structural_resource_bounds_reject_cycles_deep_trees_and_large_collections():
    cycle = []
    cycle.append(cycle)
    deep = []
    for _ in range(20):
        deep = [deep]
    for value in (cycle, deep, [None] * 100_001, "x" * (4 * 1024 * 1024 + 1), {1: "bad key"}):
        with pytest.raises(SourceAssessmentSnapshotError):
            source_assessment_report_from_dict(value)
