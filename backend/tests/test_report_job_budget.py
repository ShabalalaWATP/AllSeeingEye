"""Reservations survive failures and enforce one lifetime job allowance."""

import json
from dataclasses import replace
from uuid import UUID

import pytest

from ase.application.ports.llm import LlmGatewayError, LlmTokenBudgetExhausted
from ase.application.report_jobs.budget import (
    JobBudgetExhausted,
    JobInterrupted,
    output_used,
    token_count,
)
from ase.application.report_jobs.model_calls import BudgetedLlmGateway
from ase.domain.errors import InvalidRequest
from report_job_budget_helpers import PROFILE_ID, REQUEST, RESPONSE, Gateway, Ledger, row


async def call(ledger, gateway=None, request=REQUEST):
    return await BudgetedLlmGateway(gateway or Gateway(ledger), ledger.budget()).complete(
        "https://model.example/v1", "private-key-marker", "luna", request
    )


async def test_reserved_before_invocation_and_settled_without_content_or_credentials():
    ledger = Ledger()
    gateway = Gateway(ledger)
    assert await call(ledger, gateway) is RESPONSE
    entry = ledger.payload["calls"][0]
    UUID(entry["id"])
    assert len(entry["request_hash"]) == 64
    assert entry["status"] == "completed" and entry["error"] is None
    assert entry["model"] == "luna" and entry["schema"] == "report_section"
    assert entry["profile_id"] == str(PROFILE_ID)
    assert entry["reserved_output"] == 32000
    assert entry["prompt_tokens"] == 1000 and entry["completion_tokens"] == 800
    assert entry["latency_ms"] >= 0
    assert ledger.writes == 2 and ledger.checks == 3
    assert gateway.calls[0][3] is REQUEST
    assert "private-" not in json.dumps(ledger.payload)


@pytest.mark.parametrize("count", [0, 1, 2**31 - 1])
def test_valid_counters_remain_known(count):
    assert token_count(count) == count


@pytest.mark.parametrize("count", [True, False, -1, 2**31, 2.2, "10", None])
async def test_invalid_accounting_remains_unknown_and_reservation_is_consumed(count):
    ledger = Ledger()
    gateway = Gateway(ledger, replace(RESPONSE, prompt_tokens=count, completion_tokens=count))
    await call(ledger, gateway)
    entry = ledger.payload["calls"][0]
    assert entry["prompt_tokens"] is None and entry["completion_tokens"] is None
    assert output_used(ledger.payload) == 32000


async def test_input_counts_do_not_consume_output_allowance():
    ledger = Ledger()
    gateway = Gateway(ledger, replace(RESPONSE, prompt_tokens=2**31 - 1, completion_tokens=0))
    await call(ledger, gateway)
    assert output_used(ledger.payload) == 0
    await call(ledger, gateway)
    assert len(gateway.calls) == 2


@pytest.mark.parametrize("status", ["in_flight", "uncertain", "failed", "completed"])
async def test_unknown_outcomes_charge_the_entire_reservation(status):
    ledger = Ledger()
    ledger.payload["calls"] = [row(status=status, completion=None)] * 8
    gateway = Gateway(ledger)
    with pytest.raises(JobBudgetExhausted):
        await call(ledger, gateway)
    assert not gateway.calls and len(ledger.payload["calls"]) == 8


async def test_actual_output_above_reservation_is_not_silently_capped():
    ledger = Ledger()
    await call(ledger, Gateway(ledger, replace(RESPONSE, completion_tokens=256001)))
    with pytest.raises(JobBudgetExhausted):
        await call(ledger)


async def test_boundary_output_reservation_is_permitted_but_next_request_is_refused():
    ledger = Ledger()
    ledger.payload["calls"] = [row(completion=None)] * 7
    gateway = Gateway(ledger, replace(RESPONSE, completion_tokens=None))
    await call(ledger, gateway)
    assert output_used(ledger.payload) == 256000
    with pytest.raises(JobBudgetExhausted):
        await call(ledger, gateway)
    assert len(gateway.calls) == 1


async def test_lifetime_call_count_applies_even_to_zero_output_calls():
    ledger = Ledger()
    ledger.payload["calls"] = [row(completion=0)] * 23
    gateway = Gateway(ledger, replace(RESPONSE, completion_tokens=0))
    await call(ledger, gateway)
    with pytest.raises(JobBudgetExhausted):
        await call(ledger, gateway)
    assert len(ledger.payload["calls"]) == 24 and len(gateway.calls) == 1


async def test_known_exhaustion_is_accounted_and_identical_request_is_not_repeated():
    ledger, gateway = Ledger(), None
    gateway = Gateway(ledger)
    gateway.error = LlmTokenBudgetExhausted(model="luna", prompt_tokens=27, completion_tokens=32000)
    for _ in range(2):
        with pytest.raises(LlmTokenBudgetExhausted) as error:
            await call(ledger, gateway)
        assert error.value.completion_tokens == 32000
    assert len(gateway.calls) == 1 and len(ledger.payload["calls"]) == 1
    assert ledger.payload["calls"][0]["error"] == "token_budget_exhausted"
    gateway.error = None
    await call(ledger, gateway, replace(REQUEST, max_output_tokens=31000))
    assert len(gateway.calls) == 2


async def test_known_exhaustion_rejects_invalid_error_accounting():
    ledger = Ledger()
    gateway = Gateway(ledger)
    gateway.error = LlmTokenBudgetExhausted(model="luna", prompt_tokens=True, completion_tokens=-1)
    with pytest.raises(LlmTokenBudgetExhausted):
        await call(ledger, gateway)
    assert output_used(ledger.payload) == 32000
    assert ledger.payload["calls"][0]["prompt_tokens"] is None


async def test_gateway_failure_records_only_safe_enum_and_keeps_reservation():
    ledger = Ledger()
    gateway = Gateway(ledger)
    gateway.error = LlmGatewayError("private-upstream-body-marker")
    with pytest.raises(LlmGatewayError):
        await call(ledger, gateway)
    assert ledger.payload["calls"][0]["error"] == "provider_error"
    assert output_used(ledger.payload) == 32000
    assert "private-" not in json.dumps(ledger.payload)


@pytest.mark.parametrize("after_commit", [False, True])
async def test_failed_reservation_never_invokes_provider_or_retries_write(after_commit):
    ledger = Ledger()
    ledger.fail_write, ledger.fail_after_commit = 1, after_commit
    gateway = Gateway(ledger)
    with pytest.raises(JobInterrupted) as error:
        await call(ledger, gateway)
    assert not gateway.calls and ledger.writes == 1
    assert "private-" not in str(error.value)
    assert len(ledger.payload["calls"]) == int(after_commit)


@pytest.mark.parametrize("after_commit", [False, True])
async def test_failed_settlement_never_releases_answer_or_retries_write(after_commit):
    ledger = Ledger()
    ledger.fail_write, ledger.fail_after_commit = 2, after_commit
    gateway = Gateway(ledger)
    with pytest.raises(JobInterrupted):
        await call(ledger, gateway)
    assert len(gateway.calls) == 1 and ledger.writes == 2
    assert ledger.payload["calls"][0]["status"] == ("completed" if after_commit else "in_flight")


@pytest.mark.parametrize("check", [1, 2, 3])
async def test_access_is_checked_before_reservation_send_and_answer_release(check):
    ledger = Ledger()
    ledger.deny_check = check
    gateway = Gateway(ledger)
    with pytest.raises(PermissionError):
        await call(ledger, gateway)
    assert len(gateway.calls) == (1 if check == 3 else 0)
    assert len(ledger.payload["calls"]) == (0 if check == 1 else 1)


@pytest.mark.parametrize(
    "calls", [None, {}, [row()] * 25, [row(reserved=True)], [row(status="bad")]]
)
async def test_corrupt_ledger_fails_closed(calls):
    ledger = Ledger()
    ledger.payload["calls"] = calls
    gateway = Gateway(ledger)
    with pytest.raises(JobInterrupted):
        await call(ledger, gateway)
    assert not gateway.calls


@pytest.mark.parametrize(
    "model_request",
    [replace(REQUEST, max_output_tokens=0), replace(REQUEST, schema_name="private\nmarker")],
)
async def test_invalid_request_metadata_cannot_create_a_reservation(model_request):
    ledger = Ledger()
    with pytest.raises(InvalidRequest):
        await call(ledger, request=model_request)
    assert ledger.writes == 0
