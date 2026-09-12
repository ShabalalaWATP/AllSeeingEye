"""Model task proposals are bounded and constrained to current operator-authorised sources."""

import json
from dataclasses import asdict, replace

import pytest
from pydantic import ValidationError

from ase.api.schemas_reports import ReportCreateIn
from ase.application.reports.request import ReportRequest
from ase.application.research.model_planning import (
    admit_proposals,
    parse_proposals,
    planning_context,
)
from ase.application.research.service import ResearchCollectionService
from ase.domain.errors import InvalidRequest
from ase.domain.research_capacity import MAX_COLLECTION_PROVIDERS, MAX_PLANNED_TASKS
from ase.domain.research_planning import PlanningTrace, planning_from_dict
from ase.domain.research_records import research_from_dict, research_to_dict
from ase.domain.research_tasks import PlannedQueryTask, ResearchCandidate
from test_operator_research_tasks import Provider
from test_research_plan import QUERY


def payload():
    return {
        "candidates": [
            {"id": "alternative", "label": "Possible Acme organisation", "identifiers": ["12345"]}
        ],
        "tasks": [
            {
                "id": "distinguish",
                "source_id": "source",
                "purpose": "disambiguation",
                "terms": ["Acme 12345 alternative"],
                "candidate_id": "alternative",
            }
        ],
    }


def setup(query=None, providers=None, seeds=0, operator_terms=()):
    query = query or replace(QUERY, question="What changed for Acme 12345?", source_ids=("source",))
    providers = providers or [Provider("source")]
    collection = ResearchCollectionService(lambda _: providers)
    context = planning_context(query, collection.plan(query), seeds, operator_terms=operator_terms)
    return query, collection, context


def test_generated_tasks_are_additive_and_do_not_change_any_other_query_field():
    operator = PlannedQueryTask("check", "source", "challenge", ("operator exact terms",))
    query, collection, context = setup(
        replace(QUERY, question="Acme 12345?", planned_tasks=(operator,))
    )
    candidates, tasks = parse_proposals(json.dumps(payload()))
    revised = admit_proposals(query, context, candidates, tasks, collection, 0)
    assert (
        replace(
            revised,
            candidate_hypotheses=query.candidate_hypotheses,
            planned_tasks=query.planned_tasks,
        )
        == query
    )
    assert revised.planned_tasks[0] is operator
    model = next(
        row for row in collection.plan(revised).tasks if row.task_id == "model:distinguish"
    )
    assert model.provenance == "model_proposed_task" and model.terms == tasks[0].terms


@pytest.mark.parametrize(
    "change",
    ["source", "identifier", "duplicate", "candidate_reference", "capacity", "unsupported"],
)
def test_invalid_proposals_cannot_expand_scope_or_invent_identifiers(change):
    query, collection, context = setup()
    data = payload()
    if change == "source":
        data["tasks"][0]["source_id"] = "https://evil.invalid"
    if change == "identifier":
        data["candidates"][0]["identifiers"] = ["invented-LEI"]
    if change == "duplicate":
        query = replace(query, candidate_hypotheses=(ResearchCandidate("alternative", "Original"),))
    if change == "candidate_reference":
        data["tasks"][0]["candidate_id"] = "unknown"
    if change == "capacity":
        context["task_slots"] = 0
    if change == "unsupported":
        context["allowed_sources"] = []
    candidates, tasks = parse_proposals(json.dumps(data))
    with pytest.raises((ValueError, InvalidRequest)):
        admit_proposals(query, context, candidates, tasks, collection, 0)


def test_direction_generated_identifier_is_not_operator_grounding():
    query, collection, context = setup(
        replace(QUERY, question="What changed for Acme?", terms=("invented 12345",))
    )
    candidates, tasks = parse_proposals(json.dumps(payload()))
    with pytest.raises(ValueError, match="absent"):
        admit_proposals(query, context, candidates, tasks, collection, 0)
    context = planning_context(query, collection.plan(query), 0, operator_terms=("Acme 12345",))
    assert admit_proposals(query, context, candidates, tasks, collection, 0).planned_tasks


@pytest.mark.parametrize(
    "content",
    [
        '{"candidates":[],"tasks":[],"tasks":[]}',
        '{"candidates":[],"tasks":[],"scope":"new"}',
        "x" * 32769,
        '{"candidates":{},"tasks":[]}',
    ],
    ids=["duplicate-key", "extra-field", "oversized", "wrong-type"],
)
def test_malformed_or_oversized_output_is_rejected(content):
    with pytest.raises(ValueError):
        parse_proposals(content)


def test_seed_receipts_and_existing_tasks_share_capacity():
    query, _, context = setup(
        replace(QUERY, source_ids=None),
        providers=[
            Provider("source"),
            *(Provider(str(i)) for i in range(MAX_COLLECTION_PROVIDERS - 1)),
        ],
        seeds=MAX_PLANNED_TASKS,
    )
    assert context["task_slots"] == 0
    query, _collection, context = setup(
        replace(
            query,
            planned_tasks=tuple(
                PlannedQueryTask(f"op{i}", "source", "challenge", ("a",)) for i in range(8)
            ),
        )
    )
    assert context["task_slots"] == 0


def test_model_origin_is_output_only_and_cannot_enter_a_report_request():
    model = PlannedQueryTask("x", "source", "challenge", ("a",), origin="model")
    with pytest.raises(ValueError, match="provenance"):
        ReportRequest("ask", question="x", research_planned_tasks=(model,))
    with pytest.raises(ValidationError):
        ReportCreateIn.model_validate(
            {
                "template": "ask",
                "question": "x",
                "research_mode": "quick",
                "research_planned_tasks": [asdict(model)],
            }
        )


def test_trace_roundtrip_and_invalid_acceptance():
    candidates, tasks = parse_proposals(json.dumps(payload()))
    trace = PlanningTrace(
        "applied",
        "a" * 2048,
        "model",
        1,
        "Added for collection",
        candidates,
        tasks,
        ("alternative",),
        ("model:distinguish",),
    )
    assert planning_from_dict(asdict(trace)) == trace
    with pytest.raises(ValueError):
        replace(trace, status="rejected")
    with pytest.raises(ValueError):
        planning_from_dict({**asdict(trace), "extra": "forged"})


def test_historical_receipt_without_new_fields_retains_exact_json():

    old = {
        "question": "Legacy",
        "mode": "quick",
        "focus": "general",
        "languages": ["en"],
        "terms": ["original"],
        "since": "2026-09-01T00:00:00+00:00",
        "until": "2026-09-02T00:00:00+00:00",
        "attempts": [],
        "collected_items": 0,
        "policy_version": "ase-research-v1",
        "passes": [],
        "time_basis": "publication",
        "plan": {
            "question": "Legacy",
            "since": "2026-09-01T00:00:00+00:00",
            "until": "2026-09-02T00:00:00+00:00",
            "languages": ["en"],
            "tasks": [],
            "request_limit": 6,
            "seconds_limit": 45,
            "item_limit": 200,
            "policy_version": "ase-deterministic-plan-v1",
            "model_calls": 0,
            "translation_calls": 0,
            "replans": 0,
            "focus": "general",
            "mode": "quick",
            "subject": None,
            "country_iso": None,
            "translation": None,
            "area": None,
            "time_basis": "publication",
            "candidate_hypotheses": [
                {"id": "old", "label": "Old operator candidate", "identifiers": ["12345"]}
            ],
        },
    }
    serialised = json.dumps(old, sort_keys=True)
    restored = research_from_dict(json.loads(serialised))
    assert json.dumps(research_to_dict(restored), sort_keys=True) == serialised
