"""Only bounded current-packet prose and static failure messages reach the client."""

from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import pytest

from ase.application.report_jobs.controls import request_digest, resumed_payload
from ase.application.report_jobs.views import (
    current_sections,
    error_message,
    job_view,
    refresh_summary,
)
from ase.application.reports.request import ReportRequest
from ase.domain.errors import InvalidRequest
from report_job_helpers import job
from report_job_service_helpers import call, section

PACKET = "a" * 64


def payload():
    result = {
        "schema_version": 1,
        "input": {
            "template_id": "ask",
            "routing": {
                "profiles": [
                    {
                        "role": "assessment",
                        "model": "fixture-model",
                        "reasoning_effort": "max",
                    }
                ]
            },
        },
        "current_packet": PACKET,
        "sections": {f"{PACKET}:topic-1": section(PACKET)},
        "calls": [call("completed", completion_tokens=100), call()],
    }
    refresh_summary(result)
    return result


def test_public_fields_exclude_private_input_and_old_packet_text():
    data = payload()
    old = "b" * 64
    data["sections"][f"{old}:other"] = section(old, "other")
    data["input"]["private_note"] = "PRIVATE INPUT MUST NOT APPEAR"
    data["summary"]["private_note"] = "NOT A PUBLIC FIELD"
    value = job(status="paused", payload=data, error="private_exception_details")
    detail = job_view(value)
    assert len(detail["sections"]) == detail["completed_sections"] == 1
    assert detail["sections"][0]["citations"] == ["E1"]
    assert detail["usage"]["output_tokens"] == 32100
    assert detail["usage"]["uncertain_calls"] == 1
    assert "PRIVATE" not in str(detail) and "private_exception_details" not in str(detail)
    assert "private_note" not in str(detail) and detail["can_resume"]
    assert not job_view(value, can_control=False)["can_resume"]
    thin = replace(value, payload={"schema_version": 1, "summary": data["summary"]})
    assert job_view(thin, detail=False)["sections"] == []


def test_completed_synthesis_uses_statement_and_both_evidence_lists():
    data = payload()
    item = section(PACKET, "synthesis")
    item["payload"].update(kind="synthesis", evidence_labels=["E1", "E2"])
    item["payload"]["body"] = {
        "key_judgements": [
            {
                "statement": "The available evidence supports this cautious judgement.",
                "supporting_evidence": ["E1"],
                "contradicting_evidence": ["E2"],
            }
        ]
    }
    data["sections"] = {f"{PACKET}:synthesis": item}
    refresh_summary(data)
    result = job_view(job(payload=data, status="completed"))
    assert result["sections"][0]["reporting"] == [
        item["payload"]["body"]["key_judgements"][0]["statement"]
    ]
    assert result["sections"][0]["citations"] == ["E1", "E2"]
    assert result["report_id"] is not None and not result["can_resume"]


@pytest.mark.parametrize(
    "code",
    [
        "budget_exhausted",
        "model_changed",
        "routing_changed",
        "invalid_snapshot",
        "section_token_budget_exhausted",
    ],
)
def test_unresumable_states_are_not_offered_or_reset(code):
    value = job(status="paused", payload=payload(), error=code)
    assert not job_view(value)["can_resume"]
    with pytest.raises(InvalidRequest):
        resumed_payload(value)
    assert "private" not in (error_message(code) or "")


def test_lifetime_allowance_blocks_resume_and_split_parents_do_not_count_as_leaves():
    data = payload()
    data["calls"] = [call("uncertain") for _ in range(8)]
    data["sections"][f"{PACKET}:split"] = section(PACKET, "split", "split")
    refresh_summary(data)
    value = job(status="paused", payload=data)
    assert not job_view(value)["can_resume"]
    assert job_view(value)["total_sections"] == 1
    with pytest.raises(InvalidRequest):
        resumed_payload(value)
    assert error_message("section_invalid_synthesis") == error_message("invalid_synthesis")
    assert error_message(None) is None
    assert "unavailable" in error_message({"untrusted": "value"})


@pytest.mark.parametrize(
    "bad", [None, [], {"sections": []}, {"sections": {str(i): {} for i in range(65)}}]
)
def test_invalid_sections_fail_closed(bad):
    data = payload()
    if bad is None:
        data["current_packet"] = "not-a-digest"
    elif isinstance(bad, list):
        data["sections"] = {f"{PACKET}:topic-1": []}
    else:
        data.update(bad)
    with pytest.raises(InvalidRequest):
        current_sections(data)


@pytest.mark.parametrize(
    "part",
    ["identity", "status", "body", "reporting", "row", "citation", "text", "metadata", "title"],
)
def test_bad_checkpoint_data_never_escapes_via_detail(part):
    data = payload()
    row = data["sections"][f"{PACKET}:topic-1"]
    body = row["payload"]["body"]
    if part == "identity":
        row["section_id"] = "wrong"
    elif part == "status":
        row["status"] = "unknown"
    elif part == "body":
        row["payload"]["body"] = []
    elif part == "reporting":
        body["reporting"] = "wrong"
    elif part == "row":
        body["reporting"] = [None]
    elif part == "citation":
        body["reporting"][0]["evidence"] = ["E999"]
    elif part == "text":
        body["reporting"][0]["text"] = "control\x00text"
    elif part == "metadata":
        row["payload"] = None
    else:
        row["payload"]["title"] = None
    with pytest.raises(InvalidRequest):
        job_view(job(payload=data))


@pytest.mark.parametrize(
    "change", ["model", "effort", "input", "routing", "calls", "summary", "count"]
)
def test_malformed_summary_inputs_fail_closed(change):
    data = payload()
    if change == "model":
        data["input"]["routing"]["profiles"][0]["model"] = 23
    elif change == "effort":
        data["input"]["routing"]["profiles"][0]["reasoning_effort"] = False
    elif change == "input":
        data["input"] = []
    elif change == "routing":
        data["input"].pop("routing")
    elif change == "calls":
        data["calls"] = "wrong"
    elif change == "summary":
        data["summary"] = {}
    else:
        data["summary"]["completed_sections"] = True
    with pytest.raises(InvalidRequest):
        if change in {"summary", "count"}:
            job_view(job(payload=data))
        else:
            refresh_summary(data)


def test_request_digest_covers_original_private_reference_without_storing_it():
    request = ReportRequest("ask", question="Question", research_input_id=uuid4())
    assert request_digest(request) == request_digest(deepcopy(request))
    assert request_digest(request) != request_digest(replace(request, research_input_id=uuid4()))
    assert str(request.research_input_id) not in request_digest(request)
    with pytest.raises(InvalidRequest):
        request_digest(replace(request, question="x" * (1024 * 1024)))
    with pytest.raises(InvalidRequest):
        request_digest(replace(request, question=object()))


def test_pending_sections_do_not_release_unvalidated_partial_text():
    data = payload()
    row = data["sections"][f"{PACKET}:topic-1"]
    row["status"] = "running"
    row["payload"]["body"] = {"reporting": "UNVALIDATED PARTIAL CONTENT"}
    result = job_view(job(payload=data))
    assert "UNVALIDATED" not in str(result)
    assert result["sections"][0]["reporting"] == []
