"""AI allowance refusals never reach a provider, so they never spend report call limits."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_usage_helpers import FakeAccounting
from ase.application.report_jobs.budget import (
    MAX_CALLS,
    NOT_DISPATCHED,
    JobInterrupted,
    dispatched_calls,
)
from ase.application.report_jobs.controls import has_budget, resumed_payload
from ase.application.report_jobs.model_calls import AllowanceLlmGateway, BudgetedLlmGateway
from ase.application.report_jobs.stage_reservations import ModelStage
from ase.application.report_jobs.views import error_message, job_view, refresh_summary
from ase.application.schedules.subscription_retry_runtime import (
    automatic_retry_payload,
    classify_failure,
)
from ase.container.report_job_worker import failure_code
from ase.domain.ai_usage import AiAllowanceExceeded, AiAttribution
from ase.domain.subscription_retry import (
    RetryAction,
    RetryContext,
    RetryFailure,
    decide_retry,
)
from report_job_budget_helpers import REQUEST, Gateway, Ledger
from report_job_helpers import job
from report_job_service_helpers import call
from test_report_job_views import payload as view_payload
from test_report_stage_budget import complete, planned_ledger


def released() -> dict:
    return call() | dict(NOT_DISPATCHED)


def completed() -> dict:
    return call("completed", prompt_tokens=10, completion_tokens=100)


async def refuse(ledger: Ledger) -> None:
    inner = AllowanceLlmGateway(
        Gateway(ledger),
        FakeAccounting(reserve_error=AiAllowanceExceeded()),
        attribution=AiAttribution.actor(uuid4()),
        profile_id=None,
    )
    with pytest.raises(AiAllowanceExceeded):
        await BudgetedLlmGateway(inner, ledger.budget()).complete(
            "https://model.example", "test", "luna", REQUEST
        )


def test_released_rows_are_excluded_from_call_limits_and_resume_checks():
    data = view_payload()
    data["calls"] = [completed() for _ in range(MAX_CALLS - 1)] + [released()]
    refresh_summary(data)
    assert len(dispatched_calls(data["calls"])) == MAX_CALLS - 1
    assert has_budget(data)
    paused = job(status="paused", payload=data, error="ai_allowance_exhausted")
    view = job_view(paused)
    assert view["usage"]["calls"] == MAX_CALLS - 1
    assert view["can_resume"]
    resumed = resumed_payload(paused)
    assert len(resumed["calls"]) == MAX_CALLS - 1
    assert all(row["status"] == "completed" for row in resumed["calls"])


def test_a_ledger_of_dispatched_calls_is_still_exhausted():
    data = view_payload()
    data["calls"] = [completed() for _ in range(MAX_CALLS)]
    refresh_summary(data)
    assert not has_budget(data)
    assert not job_view(job(status="paused", payload=data, error="interrupted"))["can_resume"]


async def test_repeated_refusals_do_not_consume_the_lifetime_call_limit():
    ledger = Ledger()
    ledger.payload["calls"] = [completed() for _ in range(MAX_CALLS - 2)]
    await refuse(ledger)
    await refuse(ledger)
    assert len(ledger.payload["calls"]) == MAX_CALLS
    # The bounded ledger is full of released rows: stop resumably, never as exhausted.
    with pytest.raises(JobInterrupted):
        await refuse(ledger)
    ledger.payload["calls"] = dispatched_calls(ledger.payload["calls"])
    gateway = Gateway(ledger)
    await BudgetedLlmGateway(gateway, ledger.budget()).complete(
        "https://model.example", "test", "luna", REQUEST
    )
    assert len(gateway.calls) == 1
    assert len(dispatched_calls(ledger.payload["calls"])) == MAX_CALLS - 1


async def test_a_released_stage_call_does_not_consume_the_stage_allowance():
    ledger = planned_ledger()
    stage_row = released() | {"stage": ModelStage.INITIAL_SYNTHESIS.value}
    stage_row["reserved_output"] = 32_000
    ledger.payload["calls"].append(stage_row)
    await complete(ledger, ModelStage.INITIAL_SYNTHESIS)
    assert ledger.payload["calls"][-1]["status"] == "completed"


def test_refusal_has_a_dedicated_resumable_code_and_honest_copy():
    code = failure_code(AiAllowanceExceeded())
    assert code == "ai_allowance_exhausted"
    message = error_message(code)
    assert message is not None and "allowance" in message and "provider could not" not in message
    data = view_payload()
    data["calls"] = [completed(), released()]
    refresh_summary(data)
    assert job_view(job(status="paused", payload=data, error=code))["can_resume"]


def test_subscription_refusal_blocks_for_the_admission_probe():
    before = {"calls": [completed()], "sections": {}}
    after = {"calls": [completed(), released()], "sections": {}}
    failure = classify_failure(AiAllowanceExceeded(), "ai_allowance_exhausted", before, after)
    assert failure is RetryFailure.AI_ALLOWANCE
    now = datetime(2026, 10, 7, tzinfo=UTC)
    decision = decide_retry(RetryContext(uuid4(), failure, 1, now, now))
    assert (decision.action, decision.reason) == (RetryAction.BLOCK, "ai_allowance_exhausted")


def test_automatic_retry_drops_released_rows():
    data = {"calls": [completed(), released()], "sections": {}}
    retried = automatic_retry_payload(data)
    assert retried is not None and retried["calls"] == [data["calls"][0]]
