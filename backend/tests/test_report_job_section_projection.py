"""Accepted topic bounds and evidence gaps survive the public progress projection."""

from copy import deepcopy

import pytest

from ase.api.schemas_report_jobs import ReportJobSectionOut, public_job
from ase.application.report_jobs.views import job_view
from ase.application.reports.sections.contracts import TOPIC_SCHEMA, validate_step
from ase.domain.errors import InvalidRequest
from report_job_helpers import job
from section_model_helpers import topic_body
from test_report_job_views import PACKET, payload


def with_body(body, *, status="completed"):
    value = payload()
    row = value["sections"][f"{PACKET}:topic-1"]
    row.update(status=status)
    row["payload"]["body"] = body
    return job_view(job(payload=value))


def test_all_six_valid_reporting_items_reach_the_public_section():
    body = topic_body(["E1"])
    body["reporting"] = [
        {**body["reporting"][0], "text": f"Observation {index} was reported."}
        for index in range(TOPIC_SCHEMA["properties"]["reporting"]["maxItems"])
    ]
    validate_step(body, synthesis=False, labels=frozenset({"E1"}), eeis=frozenset())
    section = public_job(with_body(body)).sections[0]
    assert section.reporting == [row["text"] for row in body["reporting"]]
    assert len(section.reporting) == 6
    body["reporting"].append(deepcopy(body["reporting"][0]))
    with pytest.raises(InvalidRequest):
        with_body(body)


def test_gap_only_completed_topic_is_public_without_becoming_assessment():
    gap = "The retained evidence does not establish the requested local conditions."
    body = {"reporting": [], "assessment": [], "gaps": [{"text": gap, "eei": None}]}
    validate_step(body, synthesis=False, labels=frozenset({"E1"}), eeis=frozenset())
    section = public_job(with_body(body)).sections[0]
    assert section.status == "completed"
    assert section.reporting == [] and section.assessment is None
    assert section.gaps == [gap]
    assert section.citations == [] and section.error is None


@pytest.mark.parametrize("status", ["running", "incomplete", "split"])
def test_unaccepted_gap_text_is_never_released(status):
    body = {"gaps": [{"text": "UNACCEPTED PRIVATE GAP", "eei": None}]}
    result = with_body(body, status=status)
    assert result["sections"][0]["gaps"] == []
    assert "UNACCEPTED" not in str(result)


@pytest.mark.parametrize(
    "bad",
    [
        None,
        "wrong",
        ["wrong"],
        [{"text": None}],
        [{"text": "bad\x00control"}],
        [{"text": "x" * 1201}],
        [{"text": "gap"}] * 2,
    ],
)
def test_topic_gap_projection_rejects_malformed_or_unbounded_text(bad):
    body = topic_body(["E1"])
    body["gaps"] = bad
    with pytest.raises(InvalidRequest):
        with_body(body)


def test_missing_legacy_gap_field_defaults_to_empty():
    body = topic_body(["E1"])
    body.pop("gaps")
    section = with_body(body)["sections"][0]
    assert section["gaps"] == []
    section.pop("gaps")
    assert ReportJobSectionOut.model_validate(section).gaps == []
