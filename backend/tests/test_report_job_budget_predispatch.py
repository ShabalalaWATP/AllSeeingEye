"""A reservation refused by the pre-dispatch recheck is released without charge."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ase.adapters.persistence.monthly_report_usage import _call_usage
from ase.application.report_jobs.budget import (
    NOT_DISPATCHED_ERROR,
    JobInterrupted,
    output_used,
)
from ase.application.report_jobs.model_calls import BudgetedLlmGateway
from ase.container.report_job_usage import settled_usage
from ase.container.subscription_retry_runtime import automatic_retry_payload
from ase.domain.errors import Forbidden, InvalidRequest
from ase.domain.subscription_monthly_budget import MonthlyUsage
from report_job_budget_helpers import REQUEST, Gateway, Ledger


class RefusingLedger(Ledger):
    def __init__(self, error: Exception) -> None:
        super().__init__()
        self.error = error
        self.history: list[dict] = []

    async def mutate(self, callback):
        self.history.append({"calls": [dict(row) for row in self.payload["calls"]]})
        return await super().mutate(callback)

    async def check(self):
        self.checks += 1
        if self.checks == 2:
            raise self.error


@pytest.mark.parametrize("error", [Forbidden("revoked"), InvalidRequest("source disabled")])
async def test_refused_recheck_never_invokes_and_charges_nothing(error: Exception) -> None:
    ledger = RefusingLedger(error)
    gateway = Gateway(ledger)
    budget = BudgetedLlmGateway(gateway, ledger.budget())
    with pytest.raises(type(error)) as raised:
        await budget.complete("https://model.example/v1", "key", "luna", REQUEST)
    assert raised.value is error
    assert gateway.calls == []
    entry = ledger.payload["calls"][0]
    assert entry["status"] == "failed" and entry["error"] == NOT_DISPATCHED_ERROR
    assert entry["prompt_tokens"] == 0 and entry["completion_tokens"] == 0
    assert all(row.get("error") != "provider_error" for row in ledger.payload["calls"])
    assert output_used(ledger.payload) == 0
    assert automatic_retry_payload(ledger.payload) is not None

    # The settled transition emits no usage receipt and no monthly request or output.
    reserved = ledger.history[-1]
    assert reserved["calls"][0]["status"] == "in_flight"
    assert settled_usage(reserved, ledger.payload, uuid4(), datetime.now(UTC)) == []
    assert _call_usage(entry) == MonthlyUsage(0, 0)


def test_not_dispatched_settlement_with_tokens_is_rejected() -> None:
    row = {
        "id": str(uuid4()),
        "profile_id": str(uuid4()),
        "status": "in_flight",
        "reserved_output": 32000,
        "prompt_tokens": None,
        "completion_tokens": None,
        "latency_ms": 0.0,
        "error": None,
    }
    settled = row | {"status": "failed", "error": NOT_DISPATCHED_ERROR, "completion_tokens": 9}
    with pytest.raises(JobInterrupted):
        settled_usage({"calls": [row]}, {"calls": [settled]}, uuid4(), datetime.now(UTC))
