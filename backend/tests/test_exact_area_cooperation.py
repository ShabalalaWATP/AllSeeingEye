"""Exact operational geometry filters before limits without blocking the event loop."""

import asyncio
import threading
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

import ase.domain.area_membership as membership
from ase.adapters.store import memory
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.direction.areas import AoiInput, build_area
from ase.application.direction.plans import PlanEvidenceUseCase
from ase.application.warning.evaluator import evaluate_candidates
from ase.domain.collection import CollectionPlan, Pir, Sir
from ase.domain.errors import NotFound
from test_exact_reusable_areas import event, triangle
from test_warning import NOW, indicator


def test_polygon_bounds_reject_outside_points_without_edge_work(monkeypatch):
    # Bounds are a fast rejection only. Exact containment still handles all accepted candidates.
    monkeypatch.setattr(membership, "_ring_location", Mock(side_effect=AssertionError("edge work")))
    assert not membership.area_contains_event(triangle(), event(-100, 30))


async def test_indicator_filter_and_evaluation_use_a_consistent_worker_snapshot(monkeypatch):
    store = InMemoryEventStore()
    inside = event(10.2, 40.2, id="inside")
    store.upsert([inside, event(11.8, 41.8, id="outside")])
    entered, release = threading.Event(), threading.Event()
    original = memory.select_events

    def select(snapshot, query):
        entered.set()
        assert release.wait(3), "geometry ran on the event loop"
        return original(snapshot, query)

    monkeypatch.setattr(memory, "select_events", select)
    rule = indicator(countries=(), keywords=(), categories=(), research_area=triangle())
    pending = asyncio.create_task(evaluate_candidates(store, rule, NOW, None))
    try:
        async with asyncio.timeout(3):
            while not entered.is_set():
                await asyncio.sleep(0)
        # The event loop can mutate the live store while the admitted snapshot stays unchanged.
        store.upsert([replace(inside, title="Moved outside", point=event(11.8, 41.8).point)])
    finally:
        release.set()
    firing = await pending
    assert firing is not None and firing.count == 1
    assert firing.evidence == (inside,)
    assert store._waiting_reads == 0


@pytest.mark.parametrize("revoked", [False, True])
async def test_plan_evidence_uses_admitted_exact_query_and_rechecks_access(user, revoked):
    store = InMemoryEventStore()
    area = build_area(AoiInput("Exact", "geometry", research_area=triangle()), user, uuid4(), NOW)
    plan = CollectionPlan(
        uuid4(),
        "Plan",
        "",
        area.id,
        (),
        (Pir("PIR-1", "Activity", (Sir("SIR-1.1", "Activity", keywords=("Shelling",)),)),),
        True,
        user.id,
        NOW,
        NOW,
    )
    inside, outside = event(10.2, 40.2, id="inside"), event(11.8, 41.8, id="outside")
    store.upsert([inside, outside])
    decision = Mock()
    decisions = [decision, NotFound()] if revoked else [decision, decision]
    access = SimpleNamespace(context=AsyncMock(side_effect=decisions))
    plans = SimpleNamespace(get=AsyncMock(return_value=plan))
    areas = SimpleNamespace(get=AsyncMock(return_value=area))
    read = store.read_cooperatively
    calls = []

    async def capture(query, project, *, admission_key):
        calls.append((query, admission_key))
        return await read(query, project, admission_key=admission_key)

    store.read_cooperatively = capture
    service = PlanEvidenceUseCase(plans, areas, store, SimpleNamespace(now=lambda: NOW), access)
    if revoked:
        with pytest.raises(NotFound):
            await service.execute(user, plan.id)
    else:
        result = await service.execute(user, plan.id)
        assert result.considered == 1 and result.sirs[0].events == (inside,)
    assert len(calls) == 1
    assert calls[0][0].research_area == triangle()
    assert calls[0][1] == f"user:{user.id}"
    assert access.context.await_count == 2
