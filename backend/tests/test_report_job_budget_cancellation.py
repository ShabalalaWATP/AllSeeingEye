"""Cancellation and interrupted writes cannot erase reservations or replay commits."""

import asyncio
from dataclasses import replace

import pytest

from ase.application.report_jobs import budget
from ase.application.report_jobs.budget import JobBudgetExhausted, JobInterrupted, output_used
from report_job_budget_helpers import RESPONSE, Gateway, Ledger, row
from test_report_job_budget import call


async def test_provider_cancellation_records_uncertain_reservation():
    ledger = Ledger()
    gateway = Gateway(ledger)
    gateway.release = asyncio.Event()
    pending = asyncio.create_task(call(ledger, gateway))
    await gateway.entered.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    entry = ledger.payload["calls"][0]
    assert entry["status"] == "uncertain" and entry["error"] == "interrupted"
    assert entry["completion_tokens"] is None and output_used(ledger.payload) == 32000


async def test_cancellation_with_revoked_lease_preserves_original_reservation():
    ledger = Ledger()
    ledger.fail_write = 2
    gateway = Gateway(ledger)
    gateway.release = asyncio.Event()
    pending = asyncio.create_task(call(ledger, gateway))
    await gateway.entered.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    assert ledger.payload["calls"][0]["status"] == "in_flight"
    assert output_used(ledger.payload) == 32000 and ledger.writes == 2


async def test_cancellation_during_successful_settlement_finishes_one_writer():
    ledger = Ledger()
    ledger.wait_write = 2
    pending = asyncio.create_task(call(ledger))
    await ledger.wait_started.wait()
    pending.cancel()
    ledger.wait_release.set()
    with pytest.raises(asyncio.CancelledError):
        await pending
    assert ledger.payload["calls"][0]["status"] == "completed"
    assert ledger.payload["calls"][0]["completion_tokens"] == RESPONSE.completion_tokens
    assert ledger.writes == 2


async def test_settlement_deadline_keeps_reservation_and_never_returns_answer(monkeypatch):
    monkeypatch.setattr(budget, "SETTLEMENT_TIMEOUT", 0.02)
    ledger = Ledger()
    ledger.wait_write = 2
    with pytest.raises(JobInterrupted):
        async with asyncio.timeout(1):
            await call(ledger)
    assert ledger.payload["calls"][0]["status"] == "in_flight"
    assert ledger.writes == 2


async def test_cancelled_settlement_deadline_is_bounded_without_retry(monkeypatch):
    monkeypatch.setattr(budget, "SETTLEMENT_TIMEOUT", 0.02)
    ledger = Ledger()
    ledger.wait_write = 2
    pending = asyncio.create_task(call(ledger))
    await ledger.wait_started.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        async with asyncio.timeout(1):
            await pending
    assert ledger.payload["calls"][0]["status"] == "in_flight"
    assert ledger.writes == 2


async def test_repeated_cancellation_never_starts_another_writer():
    ledger = Ledger()
    ledger.wait_write = 2
    pending = asyncio.create_task(call(ledger))
    await ledger.wait_started.wait()
    pending.cancel()
    await asyncio.sleep(0)
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    assert ledger.writes == 2 and ledger.payload["calls"][0]["status"] == "in_flight"


async def test_concurrent_calls_atomically_reserve_the_remaining_allowance():
    ledger = Ledger()
    ledger.payload["calls"] = [row(completion=None)] * 7
    gateway = Gateway(ledger, replace(RESPONSE, completion_tokens=32000))
    gateway.release = asyncio.Event()
    first = asyncio.create_task(call(ledger, gateway))
    await gateway.entered.wait()
    with pytest.raises(JobBudgetExhausted):
        await call(ledger, gateway)
    gateway.release.set()
    await first
    assert len(gateway.calls) == 1 and len(ledger.payload["calls"]) == 8


@pytest.mark.parametrize("action", ["removed", "duplicate", "already_settled"])
async def test_lost_or_already_settled_call_cannot_release_output(action):
    ledger = Ledger()
    gateway = Gateway(ledger)
    gateway.release = asyncio.Event()
    pending = asyncio.create_task(call(ledger, gateway))
    await gateway.entered.wait()
    if action == "removed":
        ledger.payload["calls"].clear()
    elif action == "duplicate":
        ledger.payload["calls"].append(dict(ledger.payload["calls"][0]))
    else:
        ledger.payload["calls"][0]["status"] = "uncertain"
    gateway.release.set()
    with pytest.raises(JobInterrupted):
        await pending
    assert ledger.writes == 2
