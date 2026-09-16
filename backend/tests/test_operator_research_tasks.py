"""Explicit tasks execute under one budget without becoming verified hypotheses."""

from dataclasses import replace

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from ase.api.schemas_reports import ReportCreateIn
from ase.api.schemas_research_plan import ResearchPlanIn, ResearchPlanOut
from ase.application.reports.query_preparation import (
    record_pass_provenance,
    record_query_translation,
)
from ase.application.reports.request import ReportRequest
from ase.application.reports.research_export import research_sections
from ase.application.reports.scope import report_scope
from ase.application.reports.templates import TEMPLATES
from ase.application.research.collection import ResearchCollector
from ase.application.research.replanning import collect_with_replan
from ase.application.research.service import ResearchCollectionService
from ase.domain.errors import InvalidRequest
from ase.domain.research import CollectionStatus, ResearchFocus
from ase.domain.research_capacity import MAX_COLLECTION_PROVIDERS
from ase.domain.research_plan import QueryTransformation, QueryVariant
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from ase.domain.research_tasks import PlannedQueryTask, ResearchCandidate
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from test_research_plan import NOW, QUERY
from test_research_plan import Provider as BaseProvider


class Provider(BaseProvider):
    supports_planned_terms = True


CANDIDATE = ResearchCandidate("a", "Possible organisation A", ("registry-123",))
TASK = PlannedQueryTask("check", "source", "disambiguation", ("exact operator terms",), "a")


def query(**changes):
    return replace(QUERY, candidate_hypotheses=(CANDIDATE,), planned_tasks=(TASK,), **changes)


async def test_same_source_tasks_execute_and_retain_distinct_receipts_and_hypotheses():
    provider = Provider("source")
    selected = replace(
        query(),
        planned_tasks=(
            TASK,
            replace(TASK, id="challenge", purpose="challenge", terms=("counterexample",)),
        ),
    )
    result = await ResearchCollector([provider]).collect(selected)
    assert [row.terms for row in provider.queries] == [QUERY.terms, TASK.terms, ("counterexample",)]
    assert [row.task_id for row in result.attempts] == [
        "source:source",
        "operator:check",
        "operator:challenge",
    ]
    assert [row.purpose for row in result.attempts] == ["baseline", "disambiguation", "challenge"]
    assert result.plan.candidate_hypotheses == (CANDIDATE,)
    receipt = ResearchReceipt.build(selected, result.attempts, 0, result.plan)
    assert research_from_dict(research_to_dict(receipt)) == receipt
    assert ResearchPlanOut.model_validate(result.plan).candidate_hypotheses[0].id == "a"
    assert "unverified search context" in receipt.describe()
    assert "operator:check" in receipt.describe()
    exported = str(research_sections(receipt))
    assert "operator:check" in exported and "registry-123" in exported
    assert "not established matches" in exported


async def test_operator_tasks_interleave_and_share_quick_run_budget():
    providers = [Provider("source"), *(Provider(str(index)) for index in range(7))]
    tasks = tuple(replace(TASK, id=str(index)) for index in range(5))
    result = await ResearchCollector(providers).collect(replace(query(), planned_tasks=tasks))
    assert [row.task_id for row in result.attempts[:6]] == [
        "source:source",
        "operator:0",
        "source:0",
        "operator:1",
        "source:1",
        "operator:2",
    ]
    assert sum(len(p.queries) for p in providers) == 6
    assert result.plan.request_limit == 6 and result.plan.seconds_limit == 45
    assert all(row.status is CollectionStatus.BUDGET_EXHAUSTED for row in result.attempts[6:])


async def test_unknown_inventory_and_expanded_cap_reject_before_fetch():
    providers = [
        Provider("source"),
        *(Provider(str(index)) for index in range(MAX_COLLECTION_PROVIDERS)),
    ]
    for selected, inventory in ((query(), providers), (query(), [Provider("other")])):
        with pytest.raises((InvalidRequest, ValueError)):
            await ResearchCollector(inventory).collect(selected)
        assert all(not p.queries for p in inventory)


async def test_replan_keys_tasks_separately_and_never_changes_or_repeats_operator_terms():
    provider = Provider("source")

    async def replan(original, first, remaining):
        return replace(original, terms=("new baseline",))

    result = await collect_with_replan([provider], query(), replan)
    assert [row.terms for row in provider.queries] == [QUERY.terms, TASK.terms, ("new baseline",)]
    assert len(result.attempts) == 2
    assert [row.task_id for row in result.passes[1].attempts] == ["source:source"]
    assert result.passes[1].plan.tasks[1].terms == TASK.terms
    receipt = ResearchReceipt.build(query(), result.attempts, 0, result.plan, result.passes)
    marked = record_pass_provenance(receipt, query(), None, ())
    assert marked.passes[1].plan.tasks[1].provenance == "operator_supplied_task"
    assert research_from_dict(research_to_dict(marked)) == marked


async def test_model_cannot_edit_candidate_or_operator_task_scope():
    provider = Provider("source")

    async def replan(original, first, remaining):
        return replace(original, terms=("new",), planned_tasks=(replace(TASK, terms=("altered",)),))

    result = await collect_with_replan([provider], query(), replan)
    assert [row.terms for row in provider.queries] == [QUERY.terms, TASK.terms]
    assert len(result.passes) == 1


async def test_post_draft_challenge_does_not_replay_original_operator_tasks():
    provider = Provider("source")
    await ResearchCollectionService(lambda _: [provider]).challenge_many(
        (query(terms=("postdraft",)),)
    )
    assert len(provider.queries) == 1 and provider.queries[0].terms == ("postdraft",)
    assert provider.queries[0].planned_tasks == ()
    assert provider.queries[0].candidate_hypotheses == ()


def test_translation_never_relabels_explicit_tasks():
    plan = ResearchCollectionService(lambda _: [Provider("source")]).plan(query())
    transformed = record_query_translation(
        plan,
        QueryTransformation(
            QUERY.terms, ("en",), "fixture", "completed", (QueryVariant("en", ("translated",)),)
        ),
    )
    assert transformed.tasks[1].provenance == "operator_supplied_task"


def test_report_scope_roundtrip_and_legacy_defaults():
    body = ReportCreateIn.model_validate(
        {
            "template": "ask_the_eye",
            "question": "What changed?",
            "research_mode": "quick",
            "research_candidate_hypotheses": [
                {"id": "a", "label": CANDIDATE.label, "identifiers": ["registry-123"]}
            ],
            "research_planned_tasks": [
                {
                    "id": "check",
                    "source_id": "source",
                    "purpose": "disambiguation",
                    "terms": list(TASK.terms),
                    "candidate_id": "a",
                }
            ],
        }
    )
    request = body.to_request()
    restored = ReportRequest.from_scope(
        request.template_id, report_scope(request, next(iter(TEMPLATES.values())))
    )
    assert restored.research_candidate_hypotheses == (CANDIDATE,)
    assert restored.research_planned_tasks == (TASK,)
    assert ReportRequest.from_scope("ask_the_eye", {}).research_planned_tasks == ()
    legacy = ResearchReceipt.build(QUERY, (), 0)
    assert research_from_dict(research_to_dict(legacy)) == legacy


@pytest.mark.parametrize(
    "changes",
    [
        {"candidate_hypotheses": (CANDIDATE, CANDIDATE)},
        {"planned_tasks": (TASK, TASK)},
        {"candidate_hypotheses": ()},
        {"source_ids": ()},
        {"focus": ResearchFocus.MEDIA},
        {"focus": ResearchFocus.DOCUMENT},
    ],
)
def test_query_rejects_invalid_scope(changes):
    with pytest.raises(ValueError):
        replace(query(), **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"terms": ()},
        {"terms": ("x\n",)},
        {"terms": ("x" * 301,)},
        {"terms": ("x" * 300,) * 4},
        {"id": "../x"},
        {"candidate_id": None},
        {"purpose": "fetch"},
    ],
)
def test_task_bounds_and_controls(changes):
    with pytest.raises(ValueError):
        replace(TASK, **changes)


def test_nested_api_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        ResearchPlanIn.model_validate(
            {
                "question": "q",
                "since": QUERY.since,
                "until": NOW,
                "planned_tasks": [
                    {
                        "id": "x",
                        "source_id": "source",
                        "purpose": "challenge",
                        "terms": ["term"],
                        "url": "https://example.com",
                    }
                ],
            }
        )


@pytest.mark.usefixtures("user")
async def test_authenticated_preview_preserves_tasks_and_rejects_unavailable_sources(
    client: AsyncClient,
):
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    headers = bearer(token)
    body = {"question": "What changed?", "since": QUERY.since.isoformat(), "until": NOW.isoformat()}
    original = await client.post("/api/research/runs/plan", json=body, headers=headers)
    assert original.status_code == 200
    source = original.json()["tasks"][0]["source_id"]
    planned = {
        "id": "counter",
        "source_id": source,
        "purpose": "challenge",
        "terms": ["counterexample"],
    }
    response = await client.post(
        "/api/research/runs/plan", json={**body, "planned_tasks": [planned]}, headers=headers
    )
    assert response.status_code == 200
    tasks = response.json()["tasks"]
    assert tasks[1]["task_id"] == "operator:counter" and tasks[1]["terms"] == ["counterexample"]
    invalid = await client.post(
        "/api/research/runs/plan",
        json={**body, "planned_tasks": [{**planned, "source_id": "unknown"}]},
        headers=headers,
    )
    assert invalid.status_code == 422
