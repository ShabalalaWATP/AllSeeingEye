"""Exact candidate routing retains deadlines, source authority and temporal exclusions."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace

import pytest

from ase.adapters.research_records.company import SecSubmissionsProvider
from ase.adapters.research_records.gleif import GleifParentProvider
from ase.application.research.collection import CollectionBudget, ResearchCollector
from ase.application.research.pacing import PacedProvider, RequestPacer
from ase.application.research.source_admission import ControlledResearchProvider
from ase.domain.research import CollectionStatus, ResearchMode
from research_records_helpers import CLOCK, RecordService, submissions
from test_candidate_registry_routing import candidate_query
from test_organisation_relationships import LEI, parent_record


@pytest.mark.parametrize("mode,expected", [(ResearchMode.QUICK, 6), (ResearchMode.DETAILED, 8)])
async def test_exact_tasks_share_mode_budget_and_keep_independent_receipts(
    monkeypatch, mode, expected
):
    service = RecordService(monkeypatch, submissions())
    provider = SecSubmissionsProvider(service.http, CLOCK)
    query = candidate_query(provider.id, mode=mode)
    query = replace(
        query,
        planned_tasks=tuple(replace(query.planned_tasks[0], id=f"lookup{i}") for i in range(8)),
    )
    try:
        batch = await ResearchCollector([provider]).collect(query)
        assert len(service.requests) == expected
        assert len(batch.items) == 1  # duplicate evidence consumes only one item slot
        assert len({row.task_id for row in batch.attempts}) == 9
        assert all(
            row.status is CollectionStatus.BUDGET_EXHAUSTED
            for row in batch.attempts[expected + 1 :]
        )
    finally:
        await service.http.aclose()


class Admission:
    def __init__(self, enabled):
        self.value = enabled

    async def enabled(self, source):
        return self.value

    @asynccontextmanager
    async def guard(self):
        yield


@pytest.mark.parametrize("disable_after", [False, True])
async def test_source_control_wraps_lookup_before_and_after_fetch(monkeypatch, disable_after):
    service = RecordService(monkeypatch, submissions())
    provider = SecSubmissionsProvider(service.http, CLOCK)
    admission = Admission(disable_after)
    collect = provider.collect

    async def changed(query):
        result = await collect(query)
        admission.value = False
        return result

    provider.collect = changed
    wrapped = PacedProvider(ControlledResearchProvider(provider, admission), RequestPacer())
    try:
        batch = await ResearchCollector([wrapped]).collect(candidate_query(provider.id))
        assert len(service.requests) == int(disable_after)
        assert batch.attempts[1].status is CollectionStatus.UNAVAILABLE
        assert batch.attempts[1].registry_lookup.subject == "CIK:0000001234"
        assert not batch.items
    finally:
        await service.http.aclose()


async def test_deadline_and_cancellation_propagate_for_exact_task(monkeypatch):
    service = RecordService(monkeypatch)
    provider = SecSubmissionsProvider(service.http, CLOCK)
    started = asyncio.Event()

    async def wait(query):
        assert query.subject == "CIK:0000001234"
        started.set()
        await asyncio.Event().wait()

    provider.collect = wait
    collector = ResearchCollector([provider])
    query = candidate_query(provider.id)
    try:
        result = await collector.collect(query, budget=CollectionBudget(1, 0.01, 0.01, 1))
        assert result.attempts[1].status is CollectionStatus.TIMED_OUT
        started.clear()
        task = asyncio.create_task(collector.collect(query))
        await asyncio.wait_for(started.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        await service.http.aclose()


async def test_out_of_window_relationship_is_fetched_but_not_claimed_as_history(monkeypatch):
    service = RecordService(monkeypatch, parent_record())
    provider = GleifParentProvider(service.http, CLOCK)
    try:
        result = await ResearchCollector([provider]).collect(
            candidate_query(provider.id, "lei", LEI)
        )
        assert len(service.requests) == 1
        assert result.attempts[1].status is CollectionStatus.EMPTY
        assert result.attempts[1].result_count == 0 and not result.items
        assert "publication period" in result.attempts[1].explanation
        assert "not a historical snapshot" in result.attempts[1].explanation
    finally:
        await service.http.aclose()
