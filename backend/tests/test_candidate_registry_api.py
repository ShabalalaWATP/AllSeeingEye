"""Authenticated preview, saved scope and historical term records preserve route meaning."""

from dataclasses import asdict, replace

import pytest

from ase.api.schemas_reports import ReportCreateIn
from ase.application.reports.request import ReportRequest
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import TEMPLATES
from ase.application.research.service import ResearchCollectionService
from ase.domain.research_planning import PlanningTrace, planning_from_dict
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_candidate_registry_routing import candidate_query
from test_operator_research_tasks import Provider
from test_operator_research_tasks import query as term_query


def body():
    query = candidate_query("research-sec-submissions")
    candidate = asdict(query.candidate_hypotheses[0])
    candidate.pop("origin")
    task = asdict(query.planned_tasks[0])
    task.pop("origin")
    return {
        "question": query.question,
        "focus": "company",
        "subject": query.subject,
        "since": query.since.isoformat(),
        "until": query.until.isoformat(),
        "source_ids": list(query.source_ids),
        "candidate_hypotheses": [candidate],
        "planned_tasks": [task],
    }


@pytest.mark.usefixtures("user")
async def test_authenticated_preview_exposes_exact_route_without_fetching(client):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    payload = body()
    response = await client.post("/api/research/runs/plan", json=payload, headers=bearer(token))
    assert response.status_code == 200, response.text
    selected = [row for row in response.json()["tasks"] if row["selected"]]
    assert not selected[0]["supported"]
    assert selected[1]["supported"]
    assert selected[1]["registry_lookup"]["subject"] == "CIK:0000001234"
    assert selected[1]["registry_lookup"]["original_value"] == "1234"
    payload["planned_tasks"][0]["identifier_id"] = "invented"
    assert (
        await client.post("/api/research/runs/plan", json=payload, headers=bearer(token))
    ).status_code == 422


def test_create_request_and_saved_regeneration_keep_typed_and_legacy_identifiers():
    payload = body()
    request = ReportCreateIn.model_validate(
        {
            "template": "ask_the_eye",
            "question": payload["question"],
            "research_mode": "quick",
            "research_focus": "company",
            "research_subject": payload["subject"],
            "research_source_ids": payload["source_ids"],
            "research_candidate_hypotheses": payload["candidate_hypotheses"],
            "research_planned_tasks": payload["planned_tasks"],
        }
    ).to_request()
    restored = ReportRequest.from_scope(
        request.template_id, report_scope(request, next(iter(TEMPLATES.values())))
    )
    assert restored.research_candidate_hypotheses == request.research_candidate_hypotheses
    assert restored.research_planned_tasks == request.research_planned_tasks
    with pytest.raises(ValueError):
        replace(request, research_focus="general")


def test_old_model_term_trace_and_receipt_reserialise_without_new_defaults():
    query = term_query()
    candidate = replace(query.candidate_hypotheses[0], origin="model")
    task = replace(query.planned_tasks[0], origin="model")
    trace = PlanningTrace(
        "applied",
        "fixture",
        "fixture",
        1,
        "old plan",
        (candidate,),
        (task,),
        (candidate.id,),
        ("model:" + task.id,),
    )
    old = asdict(trace)
    old["proposed_candidates"][0].pop("registry_identifiers")
    old["proposed_tasks"][0].pop("route")
    old["proposed_tasks"][0].pop("identifier_id")
    assert planning_from_dict(old) == trace
    plan = replace(
        ResearchCollectionService(lambda _: [Provider("source")]).plan(query), planning=trace
    )
    receipt = ResearchReceipt.build(query, (), 0, plan)
    frozen = research_to_dict(receipt)
    assert frozen["plan"]["planning"] == old
    assert research_to_dict(research_from_dict(frozen)) == frozen
