"""Split synthesis progress exposes bounded accepted text without duplicated parent output."""

import json
from copy import deepcopy

import pytest

from ase.application.report_jobs.views import current_sections, job_view, refresh_summary
from ase.domain.errors import InvalidRequest
from report_job_helpers import job
from report_job_service_helpers import section
from test_report_job_views import PACKET, payload


def synthesis(identity, body, *, status="completed", parent="synthesis"):
    value = section(PACKET, identity, status)
    value["payload"].update(kind="synthesis", parent=parent, body=body)
    return value


def judgements():
    return {
        "key_judgements": [
            {
                "statement": "The evidence supports a cautious assessment.",
                "supporting_evidence": ["E1"],
                "contradicting_evidence": [],
            }
        ],
        "assumptions": [],
    }


def context():
    return {
        "sourcing_statement": "Coverage is limited to the selected public sources.",
        "gaps": [{"text": "Independent verification is unavailable.", "eei": None}],
        "collection_recommendations": ["Seek a second independent account."],
        "alternative_hypotheses": [],
        "indicators_and_warning": {"watch_condition": "normal", "changes": []},
    }


def split_payload():
    value = payload()
    value["sections"] = {
        f"{PACKET}:synthesis": synthesis("synthesis", {**judgements(), **context()}, parent=None),
        f"{PACKET}:synthesis_judgements": synthesis("synthesis_judgements", judgements()),
        f"{PACKET}:synthesis_context": synthesis("synthesis_context", context()),
    }
    refresh_summary(value)
    return value


@pytest.mark.parametrize("parent_status", ["completed", "split", "running", "incomplete"])
def test_completed_children_show_plain_context_and_do_not_duplicate_compatibility_parent(
    parent_status,
):
    value = split_payload()
    value["sections"][f"{PACKET}:synthesis"]["status"] = parent_status
    refresh_summary(value)
    original_sections = deepcopy(value["sections"])
    result = job_view(job(payload=value))
    assert result["total_sections"] == result["completed_sections"] == 2
    assert [row["id"] for row in result["sections"]] == [
        "synthesis_judgements",
        "synthesis_context",
    ]
    first, second = result["sections"]
    assert first["reporting"] == [judgements()["key_judgements"][0]["statement"]]
    assert first["citations"] == ["E1"]
    assert second["reporting"] == [] and second["citations"] == []
    assert second["assessment"] == (
        "Sourcing: Coverage is limited to the selected public sources.\n\n"
        "Collection recommendation: Seek a second independent account."
    )
    assert second["gaps"] == ["Independent verification is unavailable."]
    assert value["sections"] == original_sections


def test_partial_children_never_expose_an_unfinished_context_body():
    value = split_payload()
    pending = value["sections"][f"{PACKET}:synthesis_context"]
    pending["status"] = "running"
    pending["payload"]["body"] = {"sourcing_statement": "UNACCEPTED MODEL OUTPUT"}
    refresh_summary(value)
    result = job_view(job(payload=value))
    assert result["completed_sections"] == 1 and result["total_sections"] == 2
    assert result["sections"][1]["assessment"] is None
    assert "UNACCEPTED" not in str(result)


def test_legacy_omnibus_is_kept_when_only_other_packet_children_exist():
    value = payload()
    old = "b" * 64
    foreign = synthesis("synthesis_context", context())
    foreign["packet_digest"] = old
    value["sections"] = {
        f"{PACKET}:synthesis": synthesis("synthesis", {**judgements(), **context()}, parent=None),
        f"{old}:synthesis_context": foreign,
    }
    refresh_summary(value)
    assert [row["section_id"] for row in current_sections(value)] == ["synthesis"]
    result = job_view(job(payload=value))
    assert result["total_sections"] == 1 and result["sections"][0]["assessment"]


@pytest.mark.parametrize(
    "field,bad",
    [
        ("sourcing_statement", {"text": "must not serialise objects"}),
        ("sourcing_statement", "x" * 4001),
        ("sourcing_statement", "bad\x00control"),
        ("gaps", ["wrong shape"]),
        ("gaps", [{"text": "x" * 1201}]),
        ("gaps", [{"text": "gap"}] * 21),
        ("collection_recommendations", [{"text": "wrong shape"}]),
        ("collection_recommendations", ["recommendation"] * 9),
        ("collection_recommendations", "wrong list"),
    ],
    ids=[
        "source_object",
        "source_length",
        "source_controls",
        "gap_type",
        "gap_length",
        "gap_count",
        "recommendation_type",
        "recommendation_count",
        "recommendation_list",
    ],
)
def test_context_projection_rejects_wrong_types_and_oversized_fields(field, bad):
    value = split_payload()
    value["sections"][f"{PACKET}:synthesis_context"]["payload"]["body"][field] = bad
    with pytest.raises(InvalidRequest):
        job_view(job(payload=value))


def test_context_ignores_unknown_fields_and_accepts_empty_optional_lists():
    value = split_payload()
    body = value["sections"][f"{PACKET}:synthesis_context"]["payload"]["body"]
    body.update(gaps=[], collection_recommendations=[], internal_note="PRIVATE DETAIL")
    result = job_view(job(payload=value))
    assert result["sections"][1]["assessment"] == "Sourcing: " + context()["sourcing_statement"]
    assert "PRIVATE DETAIL" not in str(result)


def test_split_context_accepts_ten_valid_gaps_from_current_writer_schema():
    value = split_payload()
    body = value["sections"][f"{PACKET}:synthesis_context"]["payload"]["body"]
    body["gaps"] = [{"text": str(index) + "x" * 399, "eei": None} for index in range(10)]
    result = job_view(job(payload=value))["sections"][1]["gaps"]
    assert result == [row["text"] for row in body["gaps"]]
    assert len(result) == 10
    body["gaps"][0]["text"] += "x"
    with pytest.raises(InvalidRequest):
        job_view(job(payload=value))


def test_legacy_omnibus_keeps_supported_longer_gap_text():
    value = payload()
    body = {**judgements(), **context(), "gaps": [{"text": "x" * 1200, "eei": None}]}
    value["sections"] = {f"{PACKET}:synthesis": synthesis("synthesis", body, parent=None)}
    refresh_summary(value)
    assert job_view(job(payload=value))["sections"][0]["gaps"] == ["x" * 1200]


def test_canonical_storage_order_still_displays_judgements_before_context():
    value = json.loads(json.dumps(split_payload(), sort_keys=True))
    assert [row["id"] for row in job_view(job(payload=value))["sections"]] == [
        "synthesis_judgements",
        "synthesis_context",
    ]
