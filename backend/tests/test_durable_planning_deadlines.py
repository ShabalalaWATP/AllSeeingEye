"""Durable Max planning uses viable deadlines without spending short collection budgets."""

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from ase.application.reports.plan_queries import prepare_model_plan
from ase.application.reports.production_types import Totals
from ase.application.reports.replan_queries import make_replanner
from ase.application.research.pacing import RequestPacer
from ase.application.research.service import ResearchCollectionService
from ase.domain.llm import ReasoningEffort
from ase.domain.research import ResearchBatch
from production_integration_helpers import production_job
from test_continuation_review import item, payload
from test_model_research_planning import setup
from test_query_translation import Gateway
from test_research_collection import QUERY
from test_research_replanning import Recording


def record_deadlines(monkeypatch):
    deadlines = []
    timeout = asyncio.timeout

    def recorded(seconds):
        deadlines.append(seconds)
        return timeout(seconds)

    monkeypatch.setattr(asyncio, "timeout", recorded)
    return deadlines


@pytest.mark.parametrize("durable,expected", [(False, 20), (True, 120)])
async def test_initial_planning_matches_durable_transport_allowance(
    container, user, monkeypatch, durable, expected
):
    original = production_job(user, container.cipher)
    profile = replace(original.profile, reasoning_effort=ReasoningEffort.MAX)
    job = replace(original, profile=profile, version_id=uuid4() if durable else None)
    query, collection, _ = setup()
    deadlines = record_deadlines(monkeypatch)

    class ExactGateway(Gateway):
        async def complete(self, base_url, key, model, request):
            assert request.reasoning_effort is ReasoningEffort.MAX
            assert request.max_output_tokens == profile.token_budget(3000)
            assert request.schema_name == "research_plan"
            return await super().complete(base_url, key, model, request)

    async def lookup(_role):
        return profile

    totals = Totals()
    gateway = ExactGateway('{"candidates": [], "tasks": []}')
    revised, trace = await prepare_model_plan(
        job, query, collection, totals, gateway, container.cipher, lookup
    )
    assert deadlines == [expected] and trace.status == "empty" and trace.call_count == 1
    assert revised == query and gateway.calls == 1 and len(totals.usage) == 1


@pytest.mark.parametrize("remaining", [0, 0.1, 10, 20, 45, 119.9])
@pytest.mark.parametrize("with_evidence", [False, True])
async def test_max_optional_review_skips_before_dispatch_and_accounting(
    container, user, remaining, with_evidence
):
    original = production_job(user, container.cipher)
    profile = replace(original.profile, reasoning_effort=ReasoningEffort.MAX)
    job = replace(original, profile=profile, version_id=uuid4())
    cipher = SimpleNamespace(decrypt=Mock(side_effect=AssertionError("Must not decrypt")))
    gateway, totals = Gateway(), Totals()

    async def lookup(_role):
        return profile

    callback = await make_replanner(job, totals, gateway, cipher, lookup)
    batch = ResearchBatch(items=(item(),) if with_evidence else ())
    proposal = await callback(QUERY, batch, remaining)
    assert proposal.query is None and proposal.trace.decision == "continue"
    assert proposal.model_called is False
    assert "not performed" in proposal.trace.rationale
    assert "Max" in proposal.trace.rationale and "original" in proposal.trace.rationale
    assert not totals.usage and gateway.calls == 0
    cipher.decrypt.assert_not_called()


@pytest.mark.parametrize(
    "durable,effort,remaining,expected",
    [
        (True, ReasoningEffort.MAX, 120, 120),
        (True, ReasoningEffort.MAX, 150, 120),
        (True, ReasoningEffort.LOW, 12, 12),
        (True, ReasoningEffort.LOW, 90, 90),
        (False, ReasoningEffort.MAX, 10, 10),
    ],
)
async def test_admitted_review_preserves_reasoning_and_remaining_deadline(
    container, user, monkeypatch, durable, effort, remaining, expected
):
    original = production_job(user, container.cipher)
    profile = replace(original.profile, reasoning_effort=effort)
    job = replace(original, profile=profile, version_id=uuid4() if durable else None)
    batch = ResearchBatch(items=(item(),))
    deadlines = record_deadlines(monkeypatch)

    class ExactGateway(Gateway):
        async def complete(self, base_url, key, model, request):
            assert request.reasoning_effort is effort
            assert request.max_output_tokens == profile.token_budget(2400)
            return await super().complete(base_url, key, model, request)

    gateway, totals = ExactGateway(json.dumps(payload(batch))), Totals()

    async def lookup(_role):
        return profile

    callback = await make_replanner(job, totals, gateway, container.cipher, lookup)
    proposal = await callback(QUERY, batch, remaining)
    assert proposal.model_called is True and gateway.calls == 1 and len(totals.usage) == 1
    assert deadlines == [expected]


@pytest.mark.parametrize("found", [False, True])
async def test_bounded_review_does_not_spend_remaining_source_allowance(
    container, user, monkeypatch, found
):
    async def no_pacing(_self):
        pass

    monkeypatch.setattr(RequestPacer, "wait", no_pacing)
    original = production_job(user, container.cipher)
    profile = replace(original.profile, reasoning_effort=ReasoningEffort.MAX)
    job = replace(original, profile=profile, version_id=uuid4())
    providers = [Recording(str(index), found=found) for index in range(8)]
    query = replace(QUERY, source_ids=tuple(row.id for row in providers[1:]))
    gateway, totals = Gateway(), Totals()

    async def lookup(_role):
        return profile

    callback = await make_replanner(job, totals, gateway, container.cipher, lookup)
    batch = await ResearchCollectionService(lambda _: providers).collect(query, replan=callback)
    assert providers[0].queries == []
    assert [len(row.queries) for row in providers[1:]] == [1, 1, 1, 1, 1, 1, 0]
    assert all(value == query for row in providers for value in row.queries)
    assert batch.plan.model_calls == 1 and batch.plan.replans == 0
    assert batch.plan.continuation.decision == "continue"
    assert len(batch.passes) == 2 and gateway.calls == 1 and len(totals.usage) == 1
