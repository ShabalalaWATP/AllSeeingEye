"""Automatic planning executes real bounded collector tasks and freezes their provenance."""

import asyncio
import json
from dataclasses import replace
from datetime import timedelta

import pytest

from ase.application.dto import RequestContext
from ase.application.reports.plan_queries import prepare_model_plan
from ase.application.reports.production_types import Totals
from ase.application.reports.request import ReportRequest
from ase.application.reports.research_export import research_sections
from ase.application.research.service import ResearchCollectionService
from ase.domain.llm import LlmResult, LlmRole
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchFocus,
    ResearchMode,
)
from ase.domain.research_records import research_from_dict, research_to_dict
from feeds_helpers import make_event
from llm_fixture_helpers import seed_legacy_profile
from production_integration_helpers import StageGateway, production_job
from report_helpers import PROFILE
from test_model_research_planning import payload, setup
from test_operator_research_tasks import Provider
from test_query_translation import Gateway


@pytest.mark.parametrize(
    "outcome", ["applied", "empty", "invalid", "failure", "cancelled", "timeout"]
)
async def test_one_routed_call_and_truthful_accounting(container, user, monkeypatch, outcome):
    job = production_job(user, container.cipher)
    query, collection, _ = setup()
    body = {"candidates": [], "tasks": []} if outcome == "empty" else payload()
    gateway = Gateway(
        "invalid" if outcome == "invalid" else json.dumps(body),
        RuntimeError("secret raw provider body")
        if outcome == "failure"
        else asyncio.CancelledError()
        if outcome == "cancelled"
        else None,
    )
    if outcome == "timeout":

        async def wait(*args):
            await asyncio.Event().wait()

        gateway.complete = wait
        monkeypatch.setattr("ase.application.reports.plan_queries.PLANNING_SECONDS", 0.01)
    roles = []

    async def lookup(role):
        roles.append(role)
        return replace(job.profile, model="a" * 2048)

    totals = Totals()
    if outcome == "cancelled":
        with pytest.raises(asyncio.CancelledError):
            await prepare_model_plan(
                job, query, collection, totals, gateway, container.cipher, lookup
            )
    else:
        revised, trace = await prepare_model_plan(
            job, query, collection, totals, gateway, container.cipher, lookup
        )
        assert trace.call_count == 1 and trace.requested_model == "a" * 2048
        assert "secret raw" not in trace.reason
        assert trace.status == {
            "invalid": "rejected",
            "failure": "unavailable",
            "timeout": "unavailable",
        }.get(outcome, outcome)
        if outcome != "applied":
            assert revised == query
    assert roles == [LlmRole.DIRECTION]
    assert len(totals.usage) == 1 and totals.usage[0].ok == (outcome in {"applied", "empty"})


@pytest.mark.parametrize(
    "case",
    ["private", "unavailable_collection", "unsupported", "unselected", "full", "missing_profile"],
)
async def test_ineligible_planning_never_calls_model(container, user, case):
    job = production_job(user, container.cipher)
    query, collection, _ = setup()
    if case == "private":
        query = replace(query, focus=ResearchFocus.DOCUMENT)
    if case == "unavailable_collection":
        collection = None
    if case == "unsupported":
        provider = Provider("source")
        provider.supports_planned_terms = False
        collection = ResearchCollectionService(lambda _: [provider])
    if case == "unselected":
        query = replace(query, source_ids=())
    if case == "full":
        job = replace(
            job,
            seed_attempts=tuple(
                CollectionAttempt(str(i), "seed", CollectionStatus.EMPTY) for i in range(63)
            ),
        )

    async def lookup(role):
        assert case == "missing_profile"

    gateway, totals = Gateway(), Totals()
    revised, trace = await prepare_model_plan(
        job, query, collection, totals, gateway, container.cipher, lookup
    )
    assert revised == query and not gateway.calls and not totals.usage
    assert trace is None or trace.call_count == 0


async def test_production_persists_generated_plan_actual_receipts_and_usage(container, user):
    await seed_legacy_profile(container, {**PROFILE, "roles": ["assessment", "direction"]})

    class EvidenceProvider(Provider):
        async def collect(self, query):
            self.queries.append(query)
            return ResearchBatch(
                items=(
                    make_event(
                        f"model-result-{len(self.queries)}",
                        title="Acme 12345 alternative activity",
                        published_at=query.until - timedelta(minutes=1),
                    ),
                )
            )

    container.store.upsert(
        make_event(
            f"noise-{index}",
            title=f"Unrelated recent observation {index}",
            published_at=container.clock.now() - timedelta(seconds=5),
        )
        for index in range(20)
    )
    provider = EvidenceProvider("source")
    container.research = ResearchCollectionService(lambda _: [provider])

    class PlanningGateway(StageGateway):
        async def complete(self, base_url, key, model, request):
            if request.schema_name in {
                "research_plan",
                "research_continuation",
                "research_replan",
                "claim_proposals",
            }:
                self.calls.append(request.schema_name)
                values = {
                    "claim_proposals": {"claims": []},
                    "research_plan": payload(),
                    "research_continuation": {
                        "decision": "continue",
                        "basis": "insufficient_context",
                        "rationale": "Further research needed",
                        "citations": [],
                        "gaps": ["Unverified scope"],
                        "query": None,
                    },
                    "research_replan": {"terms": ["original"], "variants": []},
                }
                return LlmResult(json.dumps(values[request.schema_name]), model, 5, 10, 20)
            return await super().complete(base_url, key, model, request)

    container.llm = gateway = PlanningGateway()
    async with container.session_factory() as session:
        record, version = await container.generate_report(session).execute(
            user,
            ReportRequest(
                "ask",
                question="What changed for Acme 12345?",
                research_mode=ResearchMode.QUICK,
                research_terms=("original",),
                research_source_ids=("source",),
            ),
            RequestContext(),
        )
    assert gateway.calls.count("research_plan") == 1
    assert any(query.terms == ("Acme 12345 alternative",) for query in provider.queries)
    # Model task terms alone prioritise the older relevant evidence over newer noise.
    assert version.evidence[0].title == "Acme 12345 alternative activity"
    plan = version.research.plan
    assert plan.planning.status == "applied" and plan.planning.accepted_task_ids == (
        "model:distinguish",
    )
    assert any(
        attempt.task_id == "model:distinguish" and attempt.status == CollectionStatus.COMPLETED
        for attempt in version.research.attempts
    )
    assert plan.tasks[1].provenance == "model_proposed_task"
    assert record.scope.get("research_planned_tasks") is None
    encoded = research_to_dict(version.research)
    assert research_from_dict(encoded) == version.research
    assert "Model-proposed task" in str(research_sections(version.research))
    async with container.session_factory() as session:
        repos = container.repositories(session)
        saved = await repos.reports.get_version(record.id, 1)
        assert saved.research == version.research
        assert any(
            row.purpose == "research:planning" and row.ok
            for row in await repos.llm_usage.list_recent(30)
        )
