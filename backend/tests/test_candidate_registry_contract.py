"""Identifier intent survives API, automatic admission and frozen report formats."""

import json
from dataclasses import asdict, replace

import pytest

from ase.adapters.research_records.company import SecSubmissionsProvider
from ase.api.schemas_research_plan import ResearchPlanOut
from ase.api.schemas_research_tasks import PlannedQueryTaskIn, ResearchCandidateIn
from ase.application.reports.request import ReportRequest
from ase.application.reports.research_export import research_sections
from ase.application.research.collection import ResearchCollector
from ase.application.research.model_planning import (
    admit_proposals,
    parse_proposals,
    planning_context,
)
from ase.application.research.replanning import collect_with_replan
from ase.application.research.service import ResearchCollectionService
from ase.domain.registry_identifiers import RegistryIdentifier
from ase.domain.research import ResearchFocus
from ase.domain.research_planning import PlanningTrace, planning_from_dict
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from research_records_helpers import CLOCK, RecordService, submissions
from test_candidate_registry_routing import candidate_query


@pytest.mark.parametrize(
    "namespace,value",
    [
        ("unknown", "123"),
        ("lei", "Company name"),
        ("lei", "1234"),
        ("sec_cik", "GB:1234"),
        ("gb_company_number", "CIK:1234"),
        ("gb_company_number", "COMPANIES-HOUSE:GB:1234"),
        ("sec_cik", "0"),
        ("sec_cik", "123/456"),
        ("sec_cik", "123\n"),
    ],
)
def test_invalid_or_mixed_namespaces_reject(namespace, value):
    with pytest.raises(ValueError):
        RegistryIdentifier("id", namespace, value)


def test_references_duplicate_canonical_values_and_route_scope_are_validated():
    query = candidate_query("research-sec-submissions")
    candidate, task = query.candidate_hypotheses[0], query.planned_tasks[0]
    with pytest.raises(ValueError, match="canonical"):
        replace(
            candidate,
            registry_identifiers=(
                *candidate.registry_identifiers,
                RegistryIdentifier("alias", "sec_cik", "CIK:0000001234"),
            ),
        )
    for change in ({"identifier_id": "missing"}, {"candidate_id": "missing"}):
        with pytest.raises(ValueError):
            replace(query, planned_tasks=(replace(task, **change),))
    with pytest.raises(ValueError):
        replace(task, purpose="challenge")
    with pytest.raises(ValueError):
        replace(task, terms=("Company name",))
    for focus in (
        ResearchFocus.GENERAL,
        ResearchFocus.DOMAIN,
        ResearchFocus.DOCUMENT,
        ResearchFocus.MEDIA,
    ):
        with pytest.raises(ValueError):
            replace(query, focus=focus)
    # Legacy untyped digits stay context only and cannot satisfy an exact reference.
    with pytest.raises(ValueError):
        replace(
            query,
            candidate_hypotheses=(
                replace(candidate, registry_identifiers=(), identifiers=("1234",)),
            ),
        )


async def test_api_scope_receipt_and_export_roundtrip(monkeypatch):
    service = RecordService(monkeypatch, submissions())
    provider = SecSubmissionsProvider(service.http, CLOCK)
    query = candidate_query(provider.id)
    candidate = ResearchCandidateIn.model_validate(query.candidate_hypotheses[0])
    task = PlannedQueryTaskIn.model_validate(query.planned_tasks[0])
    assert candidate.to_domain() == query.candidate_hypotheses[0]
    assert task.to_domain() == query.planned_tasks[0]
    request = ReportRequest.from_scope(
        "fixture",
        {
            "research_mode": "quick",
            "research_focus": "company",
            "research_subject": query.subject,
            "research_candidate_hypotheses": [candidate.model_dump()],
            "research_planned_tasks": [task.model_dump()],
        },
    )
    assert request.research_planned_tasks == query.planned_tasks
    assert request.research_candidate_hypotheses == query.candidate_hypotheses
    try:
        batch = await ResearchCollector([provider]).collect(query)
        assert (
            ResearchPlanOut.model_validate(batch.plan).tasks[1].registry_lookup.subject
            == "CIK:0000001234"
        )
        receipt = ResearchReceipt.build(query, batch.attempts, len(batch.items), batch.plan)
        encoded = json.loads(json.dumps(research_to_dict(receipt)))
        assert research_from_dict(encoded) == receipt
        assert "CIK:0000001234" in str(research_sections(receipt))
        assert "disambiguation only" in receipt.describe()
    finally:
        await service.http.aclose()


async def test_model_selects_issued_reference_when_name_baseline_is_unsupported(monkeypatch):
    service = RecordService(monkeypatch, submissions())
    provider = SecSubmissionsProvider(service.http, CLOCK)
    query = replace(candidate_query(provider.id), planned_tasks=())
    collection = ResearchCollectionService(lambda _: [provider])
    context = planning_context(query, collection.plan(query), 0)
    assert context["allowed_sources"][0]["identifier_options"][0]["subject"] == "CIK:0000001234"
    payload = {
        "candidates": [],
        "tasks": [
            {
                "id": "chosen",
                "source_id": provider.id,
                "purpose": "disambiguation",
                "terms": [],
                "candidate_id": "candidate",
                "route": "candidate_identifier",
                "identifier_id": "registry",
            }
        ],
    }
    candidates, tasks = parse_proposals(json.dumps(payload))
    routed = admit_proposals(query, context, candidates, tasks, collection, 0)
    trace = PlanningTrace(
        "applied", "fixture", "fixture", 1, "admitted", candidates, tasks, (), ("model:chosen",)
    )
    assert planning_from_dict(asdict(trace)) == trace
    try:
        batch = await collection.collect(routed)
        assert batch.attempts[1].registry_lookup.subject == "CIK:0000001234"
        assert batch.plan.tasks[1].provenance == "model_proposed_task"
        for field, value in (("identifier_id", "invented"), ("candidate_id", "invented")):
            with pytest.raises(ValueError):
                admit_proposals(
                    query, context, (), (replace(tasks[0], **{field: value}),), collection, 0
                )
        payload["tasks"][0]["subject"] = "CIK:9999"
        with pytest.raises(ValueError):
            parse_proposals(json.dumps(payload))
    finally:
        await service.http.aclose()


async def test_replan_cannot_replace_or_repeat_exact_identifier(monkeypatch):
    service = RecordService(
        monkeypatch,
        {
            "cik": "1234",
            "name": "Empty",
            "filings": {"recent": {"accessionNumber": [], "filingDate": [], "form": []}},
        },
    )
    provider = SecSubmissionsProvider(service.http, CLOCK)
    query = candidate_query(provider.id)

    async def replan(original, first, remaining):
        return replace(original, terms=("new baseline",))

    try:
        result = await collect_with_replan([provider], query, replan)
        assert len(service.requests) == 1
        receipt = ResearchReceipt.build(query, result.attempts, 0, result.plan, result.passes)
        assert research_from_dict(json.loads(json.dumps(research_to_dict(receipt)))) == receipt
    finally:
        await service.http.aclose()
