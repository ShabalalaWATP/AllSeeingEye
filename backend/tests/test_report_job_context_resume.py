"""Only a confirmed exhausted legacy context may resume as smaller frozen steps."""

from copy import deepcopy
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.application.report_jobs.controls import resumed_payload
from ase.application.report_jobs.views import job_view, refresh_summary
from ase.application.reports.sections.synthesis_contracts import JUDGEMENTS, validate_part
from ase.domain.errors import InvalidRequest
from ase.domain.research import ResearchMode
from report_job_helpers import job, saved
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from report_job_service_helpers import call, section
from report_job_service_helpers import service_environment as _service_environment  # noqa: F401
from section_model_helpers import synthesis_part_body
from test_report_job_views import PACKET, payload

CONTEXT = "synthesis_context"
ALTERNATIVES = "synthesis_alternatives"
COLLECTION = "synthesis_collection"


def context_payload():
    value = payload()
    value["input"]["routing"]["profiles"][0]["max_output_tokens"] = 32000
    value["calls"] = [
        call("completed", schema="report_topic", completion_tokens=100, error=None),
        call(
            "failed",
            schema="report_context",
            completion_tokens=32000,
            error="token_budget_exhausted",
        ),
    ]
    judgements = section(PACKET, "synthesis_judgements")
    judgements["payload"].update(kind="synthesis", parent="synthesis", body={"key_judgements": []})
    context = section(PACKET, CONTEXT, "incomplete")
    context["reason"] = "token_budget_exhausted"
    context["payload"].pop("body")
    context["payload"].update(kind="synthesis", parent="synthesis")
    value["sections"].update(
        {f"{PACKET}:synthesis_judgements": judgements, f"{PACKET}:{CONTEXT}": context}
    )
    refresh_summary(value)
    return value


def paused(value):
    return job(status="paused", error="section_token_budget_exhausted", payload=value)


def test_confirmed_legacy_context_resume_retains_frozen_packet_and_paid_history():
    value = context_payload()
    original = deepcopy(value)
    progress = paused(value)
    assert job_view(progress)["can_resume"]
    assert "smaller steps" in job_view(progress)["error"]
    assert resumed_payload(progress) == original
    assert value == original
    thin = replace(progress, payload={"schema_version": 1, "summary": value["summary"]})
    assert job_view(thin, detail=False)["can_resume"]
    assert not job_view(progress, can_control=False)["can_resume"]


@pytest.mark.parametrize(
    "invalid",
    [
        "unknown_call",
        "in_flight",
        "unknown_usage",
        "provider_failure",
        "no_exhausted_call",
        "wrong_packet",
        "wrong_context_id",
        "running_context",
        "running_topic",
        "other_failure",
        "child_exhausted",
        "wrong_child_parent",
        "missing_judgements",
        "missing_budget",
        "call_capacity",
        "output_capacity",
        "stage_policy",
    ],
)
def test_unsafe_or_unsplittable_exhaustion_is_never_offered_or_resumed(invalid):  # noqa: PLR0912 - independent safety boundaries
    value = context_payload()
    parent = value["sections"][f"{PACKET}:{CONTEXT}"]
    if invalid in {"unknown_call", "in_flight"}:
        value["calls"][0]["status"] = "uncertain" if invalid == "unknown_call" else "in_flight"
    elif invalid == "unknown_usage":
        value["calls"][1]["completion_tokens"] = None
    elif invalid == "provider_failure":
        value["calls"][1]["error"] = "provider_error"
    elif invalid == "no_exhausted_call":
        value["calls"][1]["schema"] = "report_topic"
    elif invalid == "wrong_packet":
        value["current_packet"] = "b" * 64
    elif invalid == "wrong_context_id":
        parent["payload"]["id"] = "other"
    elif invalid == "running_context":
        parent["status"] = "running"
    elif invalid == "running_topic":
        value["sections"][f"{PACKET}:topic-1"]["status"] = "running"
    elif invalid == "other_failure":
        parent["reason"] = "invalid_section"
    elif invalid in {"child_exhausted", "wrong_child_parent"}:
        child = section(PACKET, ALTERNATIVES, "incomplete")
        child["reason"] = "token_budget_exhausted"
        child["payload"].update(
            kind="synthesis", parent=CONTEXT if invalid == "child_exhausted" else "other"
        )
        value["sections"][f"{PACKET}:{ALTERNATIVES}"] = child
    elif invalid == "missing_judgements":
        del value["sections"][f"{PACKET}:synthesis_judgements"]
    elif invalid == "missing_budget":
        del value["input"]["routing"]["profiles"][0]["max_output_tokens"]
    elif invalid == "call_capacity":
        value["calls"].extend(call("completed", completion_tokens=1) for _ in range(21))
    elif invalid == "output_capacity":
        value["calls"][0]["completion_tokens"] = 210000
    else:
        value["model_stage_policy"] = "ase-stage-reservations-v1"
    refresh_summary(value)
    progress = paused(value)
    if invalid == "wrong_context_id":
        with pytest.raises(InvalidRequest):
            job_view(progress)
    else:
        assert not job_view(progress)["can_resume"]
    with pytest.raises(InvalidRequest):
        resumed_payload(progress)


def test_new_child_steps_hide_only_their_current_packet_parent_and_use_known_titles():
    value = context_payload()
    for identity in (ALTERNATIVES, COLLECTION):
        child = section(PACKET, identity, "running")
        child["payload"].update(kind="synthesis", parent=CONTEXT)
        child["payload"].pop("title")
        value["sections"][f"{PACKET}:{identity}"] = child
    refresh_summary(value)
    result = job_view(paused(value))
    assert [row["id"] for row in result["sections"]] == [
        "topic-1",
        "synthesis_judgements",
        ALTERNATIVES,
        COLLECTION,
    ]
    assert [row["title"] for row in result["sections"][-2:]] == [
        "Alternatives and warning",
        "Gaps and collection",
    ]
    assert result["total_sections"] == 4


async def test_service_resume_uses_same_exception_and_keeps_retained_exhausted_call(service_env):
    env = service_env
    value = context_payload()
    record = replace(paused(value), owner_id=env.user.id)
    await saved(env.factory, record)
    async with env.service() as (service, _deps):
        response = await service.resume(env.user, record.id, check_session=AsyncMock())
    assert response["status"] == "queued"
    async with env.factory() as session:
        retained = await SqlReportJobRepository(session).get(record.id)
    assert retained.payload["calls"] == value["calls"]
    assert retained.payload["sections"] == value["sections"]


@pytest.mark.parametrize("count", [3, 4])
def test_accepted_deep_and_advanced_alternatives_project_text_warning_and_citations(count):
    value = context_payload()
    child = section(PACKET, ALTERNATIVES)
    child["payload"].update(
        kind="synthesis",
        parent=CONTEXT,
        body={
            "alternative_hypotheses": [
                {
                    "text": f"Alternative {index}",
                    "why_less_likely": "Limited support",
                    "evidence": ["E1"],
                }
                for index in range(count)
            ],
            "indicators_and_warning": {
                "watch_condition": "normal",
                "changes": ["Seek confirmation"],
            },
        },
    )
    value["sections"][f"{PACKET}:{ALTERNATIVES}"] = child
    refresh_summary(value)
    projected = next(
        row for row in job_view(paused(value))["sections"] if row["id"] == ALTERNATIVES
    )
    assert all(f"Alternative {index}" in projected["assessment"] for index in range(count))
    assert "Watch for: Seek confirmation" in projected["assessment"]
    assert projected["citations"] == ["E1"]
    child["payload"]["body"]["alternative_hypotheses"][0]["evidence"] = ["E999"]
    with pytest.raises(InvalidRequest):
        job_view(paused(value))


def test_summary_hint_cannot_authorise_resume_without_the_retained_packet():
    value = context_payload()
    hint = {"schema_version": 1, "summary": value["summary"]}
    assert job_view(paused(hint), detail=False)["can_resume"]
    with pytest.raises(InvalidRequest):
        resumed_payload(paused(hint))


def test_advanced_eight_accepted_judgements_remain_readable():
    value = context_payload()
    body = synthesis_part_body(JUDGEMENTS, ["E1"])
    first = body["key_judgements"][0]
    body["key_judgements"] = [dict(first, id=f"J{index}") for index in range(1, 9)]
    accepted = validate_part(
        body,
        part=JUDGEMENTS,
        labels=frozenset({"E1"}),
        eeis=frozenset(),
        research_mode=ResearchMode.ADVANCED,
    )
    value["sections"][f"{PACKET}:{JUDGEMENTS}"]["payload"]["body"] = accepted
    projected = next(row for row in job_view(paused(value))["sections"] if row["id"] == JUDGEMENTS)
    assert len(projected["reporting"]) == 8
    assert projected["citations"] == ["E1"]
