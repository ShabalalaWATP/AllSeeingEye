"""Opt-in stage limits share the existing atomic reservation; legacy work stays valid."""

import asyncio
import json
from copy import deepcopy
from dataclasses import replace
from uuid import uuid4

import pytest

from ase.application.ports.llm import LlmGatewayError
from ase.application.ports.web_search import WebSearchRequest, WebSearchResult
from ase.application.report_jobs.budget import (
    JobBudgetExhausted,
    JobInterrupted,
    ReportCallBudget,
    output_used,
)
from ase.application.report_jobs.controls import resumed_payload
from ase.application.report_jobs.model_calls import BudgetedLlmGateway, BudgetedWebSearchGateway
from ase.application.report_jobs.stage_budget import PLAN_KEY, POLICY_KEY, freeze_stage_budget
from ase.application.report_jobs.stage_reservations import ModelStage as Stage
from ase.application.report_jobs.stage_reservations import StageDemand, build_stage_plan
from report_job_budget_helpers import REQUEST, RESPONSE, Gateway, Ledger, row
from report_job_helpers import job


def planned_ledger(*extra, call_limit=24, output_token_limit=256_000):
    ledger = Ledger()
    ledger.payload["schema_version"] = 1
    plan = build_stage_plan(
        (
            StageDemand(Stage.INITIAL_SYNTHESIS, 1, 32_000),
            StageDemand(Stage.FINAL_ADJUDICATION, 1, 32_000),
            *extra,
        ),
        call_limit=call_limit,
        output_token_limit=output_token_limit,
    )
    freeze_stage_budget(ledger.payload, plan)
    return ledger


def required_budget(ledger):
    return ReportCallBudget(ledger.mutate, ledger.check, require_stage_plan=True)


async def complete(ledger, stage, *, gateway=None, budget=None, request=REQUEST):
    wrapped = BudgetedLlmGateway(
        gateway or Gateway(ledger), budget or required_budget(ledger), stage=stage
    )
    return await wrapped.complete("https://provider.example/v1", "test", "selected-model", request)


def test_freeze_is_once_only_json_safe_and_contains_no_provider_controls():
    ledger = planned_ledger()
    snapshot = deepcopy(ledger.payload)
    assert json.loads(json.dumps(snapshot)) == snapshot
    assert ledger.writes == 0
    with pytest.raises(ValueError, match="new, unpaid"):
        freeze_stage_budget(ledger.payload, build_stage_plan(()))
    assert ledger.payload == snapshot


@pytest.mark.parametrize("calls", [None, {}, [row()]])
def test_cannot_attach_stage_plan_to_paid_or_malformed_legacy_history(calls):
    payload = {"calls": calls}
    before = deepcopy(payload)
    with pytest.raises(ValueError):
        freeze_stage_budget(payload, build_stage_plan(()))
    assert payload == before


def test_refused_plan_never_adds_opt_in_markers():
    payload = {"calls": []}
    with pytest.raises(ValueError):
        freeze_stage_budget(payload, build_stage_plan(()))
    assert payload == {"calls": []}


async def test_opt_in_call_persists_stage_before_unchanged_provider_request():
    ledger = planned_ledger()
    gateway = Gateway(ledger)
    result = await complete(ledger, Stage.INITIAL_SYNTHESIS, gateway=gateway)
    assert result is RESPONSE and gateway.calls[0][3] is REQUEST
    assert ledger.payload["calls"][0]["stage"] == "initial_synthesis"
    assert ledger.payload["calls"][0]["status"] == "completed"
    assert ledger.writes == 2


@pytest.mark.parametrize("stage", [None, "initial_synthesis", Stage.SPECIALIST])
async def test_unclassified_unknown_or_unallocated_calls_never_dispatch(stage):
    ledger = planned_ledger()
    gateway = Gateway(ledger)
    before = deepcopy(ledger.payload)
    with pytest.raises(JobBudgetExhausted):
        await complete(ledger, stage, gateway=gateway)
    assert not gateway.calls and ledger.payload == before


async def test_opt_in_marker_enforces_even_without_worker_required_flag():
    ledger = planned_ledger()
    gateway = Gateway(ledger)
    with pytest.raises(JobBudgetExhausted):
        await complete(ledger, None, gateway=gateway, budget=ledger.budget())
    assert not gateway.calls and not ledger.payload["calls"]


async def test_direct_budget_invocation_cannot_bypass_required_stage():
    ledger = planned_ledger()
    invoked = False

    async def provider():
        nonlocal invoked
        invoked = True
        return RESPONSE

    with pytest.raises(JobBudgetExhausted):
        await required_budget(ledger).run(
            request_hash="a" * 64,
            schema="anything",
            model="selected-model",
            reserved_output=32_000,
            invoke=provider,
        )
    assert not invoked and not ledger.payload["calls"]


@pytest.mark.parametrize("removed", [POLICY_KEY, PLAN_KEY, "both"])
async def test_required_worker_rejects_missing_markers_before_paid_call(removed):
    ledger = planned_ledger()
    for key in (POLICY_KEY, PLAN_KEY) if removed == "both" else (removed,):
        ledger.payload.pop(key)
    gateway = Gateway(ledger)
    with pytest.raises(JobInterrupted):
        await complete(ledger, Stage.INITIAL_SYNTHESIS, gateway=gateway)
    assert not gateway.calls and not ledger.payload["calls"]


@pytest.mark.parametrize("key,value", [(POLICY_KEY, "unknown"), (PLAN_KEY, None), (PLAN_KEY, {})])
async def test_invalid_policy_is_not_treated_as_legacy(key, value):
    ledger = planned_ledger()
    ledger.payload[key] = value
    gateway = Gateway(ledger)
    with pytest.raises(JobInterrupted):
        await complete(ledger, Stage.INITIAL_SYNTHESIS, gateway=gateway, budget=ledger.budget())
    assert not gateway.calls


async def test_profile_binding_keeps_required_policy_when_both_markers_are_absent():
    ledger = Ledger()
    budget = required_budget(ledger).with_profile(uuid4())
    gateway = Gateway(ledger)
    with pytest.raises(JobInterrupted):
        await complete(ledger, Stage.INITIAL_SYNTHESIS, gateway=gateway, budget=budget)
    assert not gateway.calls


async def test_legacy_untagged_history_and_payload_shape_remain_usable():
    ledger = Ledger()
    ledger.payload["calls"] = [row(status="uncertain", completion=None)]
    old = deepcopy(ledger.payload["calls"][0])
    await complete(ledger, None, budget=ledger.budget())
    assert ledger.payload["calls"][0] == old
    assert all("stage" not in entry for entry in ledger.payload["calls"])
    assert PLAN_KEY not in ledger.payload and POLICY_KEY not in ledger.payload
    assert output_used(ledger.payload) == 32_000 + RESPONSE.completion_tokens


async def test_atomic_stage_count_prevents_two_concurrent_calls_using_one_slot():
    ledger = planned_ledger(StageDemand(Stage.SPECIALIST, 1, 32_000))
    gateway = Gateway(ledger)
    gateway.release = asyncio.Event()
    first = asyncio.create_task(complete(ledger, Stage.SPECIALIST, gateway=gateway))
    await gateway.entered.wait()
    try:
        with pytest.raises(JobBudgetExhausted):
            await complete(ledger, Stage.SPECIALIST, gateway=gateway)
        assert len(gateway.calls) == 1 and len(ledger.payload["calls"]) == 1
    finally:
        gateway.release.set()
        await first


async def test_cancel_resume_retains_stage_and_unknown_reservation_without_free_retry():
    ledger = planned_ledger()
    gateway = Gateway(ledger)
    gateway.release = asyncio.Event()
    pending = asyncio.create_task(complete(ledger, Stage.INITIAL_SYNTHESIS, gateway=gateway))
    await gateway.entered.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    initial = deepcopy(ledger.payload)
    ledger.payload = resumed_payload(job(payload=ledger.payload))
    assert ledger.payload[PLAN_KEY] == initial[PLAN_KEY]
    assert ledger.payload["calls"][0]["stage"] == "initial_synthesis"
    assert ledger.payload["calls"][0]["status"] == "uncertain"
    assert output_used(ledger.payload) == 32_000
    with pytest.raises(JobBudgetExhausted):
        await complete(ledger, Stage.INITIAL_SYNTHESIS)
    await complete(ledger, Stage.FINAL_ADJUDICATION)
    assert len(ledger.payload["calls"]) == 2


async def test_failed_call_and_changed_request_do_not_reset_stage_dispatch_allowance():
    ledger = planned_ledger()
    gateway = Gateway(ledger)
    gateway.error = LlmGatewayError("provider failure")
    with pytest.raises(LlmGatewayError):
        await complete(ledger, Stage.INITIAL_SYNTHESIS, gateway=gateway)
    assert ledger.payload["calls"][0]["status"] == "failed"
    with pytest.raises(JobBudgetExhausted):
        await complete(ledger, Stage.INITIAL_SYNTHESIS, request=replace(REQUEST, schema_name="new"))
    assert len(ledger.payload["calls"]) == 1 and output_used(ledger.payload) == 32_000


async def test_omitted_fresh_web_cannot_bypass_shared_stage_budget():
    ledger = planned_ledger(StageDemand(Stage.FRESH_WEB, 1, 16_000), call_limit=2)
    gateway = Gateway(ledger)
    with pytest.raises(JobBudgetExhausted):
        await BudgetedWebSearchGateway(gateway, required_budget(ledger)).search(
            "test", "model", WebSearchRequest("public question", 16_000, None)
        )
    assert not gateway.calls and not ledger.payload["calls"]


async def test_fresh_web_records_explicit_stage_and_same_ledger_unchanged_request():
    ledger = planned_ledger(StageDemand(Stage.FRESH_WEB, 1, 16_000))
    result = WebSearchResult("result", (), (), "model", 2, 1, 100, 200)
    gateway = Gateway(ledger, result)
    request = WebSearchRequest("public question", 16_000, None)
    returned = await BudgetedWebSearchGateway(gateway, required_budget(ledger)).search(
        "test", "model", request
    )
    assert returned is result and gateway.calls[0][3] is request
    assert ledger.payload["calls"][0]["stage"] == "fresh_web"
    with pytest.raises(JobBudgetExhausted):
        await BudgetedWebSearchGateway(gateway, required_budget(ledger)).search(
            "test", "model", request
        )
    assert len(gateway.calls) == 1


async def test_runtime_overrun_preserves_remaining_mandatory_capacity():
    ledger = planned_ledger(
        StageDemand(Stage.DIRECTION, 1, 32_000),
        StageDemand(Stage.SPECIALIST, 1, 32_000),
        output_token_limit=128_000,
    )
    await complete(
        ledger,
        Stage.DIRECTION,
        gateway=Gateway(ledger, replace(RESPONSE, completion_tokens=40_000)),
    )
    gateway = Gateway(ledger)
    with pytest.raises(JobBudgetExhausted):
        await complete(ledger, Stage.SPECIALIST, gateway=gateway)
    assert not gateway.calls
    await complete(ledger, Stage.INITIAL_SYNTHESIS)
    await complete(ledger, Stage.FINAL_ADJUDICATION)


async def test_mismatched_output_budget_is_refused_without_changing_the_profile():
    ledger = planned_ledger()
    gateway = Gateway(ledger)
    with pytest.raises(JobBudgetExhausted):
        await complete(
            ledger,
            Stage.INITIAL_SYNTHESIS,
            gateway=gateway,
            request=replace(REQUEST, max_output_tokens=16_000),
        )
    assert not gateway.calls and not ledger.payload["calls"]
