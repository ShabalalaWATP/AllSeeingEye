"""Frozen optional web discovery has one durable, generated-context dispatch."""

import asyncio
from copy import deepcopy
from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.application.ports.web_search import WebSearchError, WebSearchRequest
from ase.application.report_jobs.budget import JobBudgetExhausted
from ase.application.report_jobs.controls import resumed_payload
from ase.application.report_jobs.fresh_web_allocation import (
    WEB_PLAN_KEY,
    freeze_web_discovery,
    validate_web_discovery_plan,
    web_discovery_plan,
)
from ase.application.report_jobs.model_calls import BudgetedWebSearchGateway
from ase.application.reports.fresh_web_research import FreshWebResearch
from ase.application.reports.production_types import Totals
from ase.application.reports.request import ReportRequest
from ase.application.research.phase_ledger import LEDGER_KEY, new_phase_ledger
from ase.domain.research import ResearchMode
from ase.domain.web_research import (
    WEB_ALLOCATION_POLICY,
    WebResearchRecord,
    web_research_from_dict,
    web_research_to_dict,
)
from ase.infrastructure.rate_limit import InMemorySlidingWindowLimiter
from helpers import FakeClock
from report_job_budget_helpers import Gateway, Ledger
from report_job_helpers import job
from report_job_helpers import job_storage as _job_storage  # noqa: F401
from report_job_service_helpers import service_environment as _service_environment  # noqa: F401
from web_search_helpers import NOW, QUERY, RESULT, Admission, Cipher, profile
from web_search_helpers import job as research_job


def web_ledger() -> Ledger:
    ledger = Ledger()
    ledger.payload["schema_version"] = 1
    ledger.payload[LEDGER_KEY] = new_phase_ledger(ResearchMode.QUICK)
    freeze_web_discovery(ledger.payload)
    return ledger


async def search(ledger: Ledger, gateway: Gateway, context: str = "public question"):
    return await BudgetedWebSearchGateway(gateway, ledger.budget()).search(
        "fixture-key", "fixture-model", WebSearchRequest(context, 8_000, None)
    )


async def test_admission_freezes_opt_in_web_plan_before_paid_work(service_env):
    request = ReportRequest(
        "ask",
        question="What changed?",
        research_mode=ResearchMode.QUICK,
        research_web_search=True,
    )
    async with service_env.service() as (service, deps):
        candidate = await service.prepare_candidate(service_env.user, uuid4(), request)
        assert candidate.payload[WEB_PLAN_KEY] == web_discovery_plan()
        assert candidate.payload["calls"] == []
        assert LEDGER_KEY in candidate.payload
        admitted = await service.admit_prepared(
            service_env.user, candidate, check_session=AsyncMock()
        )
        await deps.session.commit()
        stored = await deps.repo.get(admitted.id)
        assert stored is not None
        assert stored.payload[WEB_PLAN_KEY] == web_discovery_plan()
        assert stored.payload[LEDGER_KEY] == candidate.payload[LEDGER_KEY]

    without_web = replace(request, research_web_search=False)
    async with service_env.service() as (service, _):
        candidate = await service.prepare_candidate(service_env.user, uuid4(), without_web)
        assert WEB_PLAN_KEY not in candidate.payload


@pytest.mark.parametrize("calls", [None, {}, [{"status": "uncertain"}]])
def test_plan_cannot_be_attached_to_legacy_or_paid_payload(calls):
    payload = {"calls": calls}
    with pytest.raises(ValueError):
        freeze_web_discovery(payload)
    assert payload == {"calls": calls}


def test_frozen_plan_rejects_tampered_caps_and_type_coercion():
    plan = web_discovery_plan()
    assert validate_web_discovery_plan(plan) == plan
    for key, value in (
        ("request_limit", 2),
        ("request_limit", True),
        ("evidence_role", "original_evidence"),
        ("output_token_limit", 16001),
    ):
        with pytest.raises(ValueError, match="invalid"):
            validate_web_discovery_plan({**plan, key: value})


async def test_failed_web_call_and_changed_query_cannot_reset_allowance_or_source_phase():
    ledger = web_ledger()
    source_before = deepcopy(ledger.payload[LEDGER_KEY])
    gateway = Gateway(ledger, RESULT)
    gateway.error = WebSearchError("fixture failure")
    with pytest.raises(WebSearchError):
        await search(ledger, gateway)
    assert ledger.payload["calls"][0]["status"] == "failed"
    gateway.error = None
    with pytest.raises(JobBudgetExhausted, match="fresh-web"):
        await search(ledger, gateway, "changed public question")
    assert len(gateway.calls) == len(ledger.payload["calls"]) == 1
    assert ledger.payload[LEDGER_KEY] == source_before


async def test_cancelled_web_call_stays_uncertain_and_resume_cannot_dispatch_again():
    ledger = web_ledger()
    gateway = Gateway(ledger, RESULT)
    gateway.release = asyncio.Event()
    pending = asyncio.create_task(search(ledger, gateway))
    await gateway.entered.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    assert ledger.payload["calls"][0]["status"] == "uncertain"
    assert ledger.payload["calls"][0]["reserved_output"] == 8_000
    source_before = deepcopy(ledger.payload[LEDGER_KEY])
    ledger.payload = resumed_payload(job(payload=ledger.payload))
    assert ledger.payload[WEB_PLAN_KEY] == web_discovery_plan()
    with pytest.raises(JobBudgetExhausted, match="fresh-web"):
        await search(ledger, gateway, "new public question")
    assert len(gateway.calls) == len(ledger.payload["calls"]) == 1
    assert ledger.payload[LEDGER_KEY] == source_before


async def test_successful_web_dispatch_uses_existing_model_ledger_only():
    ledger = web_ledger()
    source_before = deepcopy(ledger.payload[LEDGER_KEY])
    gateway = Gateway(ledger, RESULT)
    assert await search(ledger, gateway) is RESULT
    assert ledger.payload["calls"][0]["schema"] == "web_search"
    assert ledger.payload["calls"][0]["status"] == "completed"
    assert ledger.payload[LEDGER_KEY] == source_before
    with pytest.raises(JobBudgetExhausted):
        await search(ledger, gateway)


async def test_frozen_receipt_names_generated_context_caps_and_no_evidence():
    ledger = web_ledger()
    gateway = Gateway(ledger, RESULT)
    clock = FakeClock(NOW)
    service = FreshWebResearch(
        BudgetedWebSearchGateway(gateway, ledger.budget()),
        Admission(),
        clock,
        InMemorySlidingWindowLimiter(clock),
        allocation_plan=ledger.payload[WEB_PLAN_KEY],
    )

    async def lookup(_):
        return profile()

    record = await service.collect(research_job(), QUERY, Totals(), Cipher(), lookup)
    assert record.status == "completed"
    assert record.allocation_version == WEB_ALLOCATION_POLICY
    assert (
        record.allocated_requests,
        record.allocated_tool_calls,
        record.allocated_seconds,
        record.allocated_output_tokens,
    ) == (1, 3, 90, 16_000)
    assert web_research_from_dict(web_research_to_dict(record)) == record
    assert "not a publisher excerpt" in record.describe()
    assert "Do not cite it as E-labelled evidence" in record.describe()
    assert ledger.payload["calls"][0]["schema"] == "web_search"

    again = await service.collect(research_job(), QUERY, Totals(), Cipher(), lookup)
    assert again.status == "not_collected" and again.request_count == 0
    assert "allowance was exhausted" in again.explanation
    assert again.allocation_version == WEB_ALLOCATION_POLICY
    assert len(gateway.calls) == 1


def test_legacy_web_record_without_allocation_fields_is_still_readable():
    old = web_research_to_dict(WebResearchRecord("not_collected", "Legacy", NOW))
    for key in (
        "allocation_version",
        "allocated_requests",
        "allocated_tool_calls",
        "allocated_seconds",
        "allocated_output_tokens",
    ):
        old.pop(key)
    record = web_research_from_dict(old)
    assert record is not None and record.allocation_version is None
    assert record.allocated_requests == 0
