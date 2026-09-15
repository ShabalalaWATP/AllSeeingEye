"""The budget wrapper preserves all model controls and fingerprints complete requests."""

import json
from dataclasses import replace
from uuid import uuid4

import pytest

from ai_usage_helpers import FakeAccounting
from ase.application.ports.llm import LlmTokenBudgetExhausted
from ase.application.ports.web_search import WebSearchError, WebSearchRequest, WebSearchResult
from ase.application.report_jobs.budget import CallNotDispatched, ReportCallBudget, output_used
from ase.application.report_jobs.model_calls import (
    AllowanceLlmGateway,
    BudgetedLlmGateway,
    BudgetedWebSearchGateway,
)
from ase.domain.ai_usage import AiAllowanceExceeded, AiAttribution, AiCallOutcome
from ase.domain.errors import InvalidRequest
from ase.domain.llm import LlmImage, LlmMessage, LlmProvider, LlmResult, ReasoningEffort
from report_job_budget_helpers import REQUEST, Gateway, Ledger
from test_report_job_budget import call

WEB_REQUEST = WebSearchRequest("private-query-marker", 16000, ReasoningEffort.MAX)
WEB_RESPONSE = WebSearchResult("private-output-marker", (), (), "luna", 1, 4, 100, 200)


class RawGateway:
    def __init__(self, result: LlmResult | None = None, error: Exception | None = None):
        self.result = result or LlmResult("{}", "luna", 1, 12, 34)
        self.error = error

    async def complete(self, *_args):
        if self.error is not None:
            raise self.error
        return self.result


@pytest.mark.parametrize("provider", [LlmProvider.OPENAI_COMPATIBLE, LlmProvider.BEDROCK])
async def test_request_and_provider_are_forwarded_unchanged(provider):
    ledger = Ledger()
    gateway = Gateway(ledger)
    request = replace(REQUEST, provider=provider)
    wrapped = BudgetedLlmGateway(gateway, ledger.budget())
    await wrapped.complete("https://provider.example/v1", "secret-test", "selected-model", request)
    assert gateway.calls == [
        ("https://provider.example/v1", "secret-test", "selected-model", request)
    ]
    assert gateway.calls[0][3] is request


@pytest.mark.parametrize(
    "model_request",
    [
        replace(REQUEST, messages=(LlmMessage("user", "changed question"),)),
        replace(REQUEST, messages=(LlmMessage("system", "private-question-marker"),)),
        replace(REQUEST, reasoning_effort=ReasoningEffort.HIGH),
        replace(REQUEST, provider=LlmProvider.BEDROCK),
        replace(REQUEST, temperature=0.8),
        replace(REQUEST, json_schema={"type": "string"}),
        replace(REQUEST, schema_name="report_summary"),
        replace(REQUEST, max_output_tokens=16000),
        replace(
            REQUEST,
            messages=(
                LlmMessage(
                    "user", "private-question-marker", (LlmImage(b"\x89PNG\r\n\x1a\n" + b"0" * 20),)
                ),
            ),
        ),
    ],
)
async def test_meaningful_request_change_has_different_fingerprint(model_request):
    ledger = Ledger()
    await call(ledger)
    await call(ledger, request=model_request)
    assert ledger.payload["calls"][0]["request_hash"] != ledger.payload["calls"][1]["request_hash"]


async def test_schema_order_and_key_rotation_do_not_reset_exhausted_request_guard():
    ledger = Ledger()
    gateway = Gateway(ledger)
    gateway.error = LlmTokenBudgetExhausted(model="luna")
    wrapped = BudgetedLlmGateway(gateway, ledger.budget())
    for key, schema in [("old", {"a": 1, "b": 2}), ("new", {"b": 2, "a": 1})]:
        with pytest.raises(LlmTokenBudgetExhausted):
            await wrapped.complete(
                "https://provider.example/v1", key, "luna", replace(REQUEST, json_schema=schema)
            )
    assert len(gateway.calls) == 1


async def test_changed_endpoint_and_model_are_part_of_request_fingerprint():
    ledger = Ledger()
    gateway = Gateway(ledger)
    wrapped = BudgetedLlmGateway(gateway, ledger.budget())
    for endpoint, model in [
        ("https://a.example", "a"),
        ("https://b.example", "a"),
        ("https://a.example", "b"),
    ]:
        await wrapped.complete(endpoint, "test", model, REQUEST)
    assert len({entry["request_hash"] for entry in ledger.payload["calls"]}) == 3


@pytest.mark.parametrize("schema", [{"number": float("nan")}, {"bad": object()}])
async def test_noncanonical_requests_fail_before_reservation(schema):
    ledger = Ledger()
    with pytest.raises(InvalidRequest):
        await call(ledger, request=replace(REQUEST, json_schema=schema))
    assert not ledger.writes


async def test_web_search_uses_same_ledger_and_preserves_request_controls():
    ledger = Ledger()
    await call(ledger)
    gateway = Gateway(ledger, WEB_RESPONSE)
    result = await BudgetedWebSearchGateway(gateway, ledger.budget()).search(
        "private-key", "luna", WEB_REQUEST
    )
    assert result is WEB_RESPONSE
    assert gateway.calls == [("web", "private-key", "luna", WEB_REQUEST)]
    assert gateway.calls[0][3] is WEB_REQUEST
    assert ledger.payload["calls"][1]["schema"] == "web_search"
    assert output_used(ledger.payload) == 1000
    assert "private-" not in json.dumps(ledger.payload)


async def test_web_known_exhaustion_is_not_automatically_repeated():
    ledger = Ledger()
    gateway = Gateway(
        ledger,
        replace(
            WEB_RESPONSE, failure="The model did not finish within its web-search output budget."
        ),
    )
    wrapped = BudgetedWebSearchGateway(gateway, ledger.budget())
    assert (await wrapped.search("test", "luna", WEB_REQUEST)).failure
    with pytest.raises(LlmTokenBudgetExhausted):
        await wrapped.search("test", "luna", WEB_REQUEST)
    assert len(gateway.calls) == 1
    assert ledger.payload["calls"][0]["status"] == "failed"
    assert ledger.payload["calls"][0]["completion_tokens"] == 200


async def test_web_other_failure_records_only_safe_enum():
    ledger = Ledger()
    gateway = Gateway(ledger, replace(WEB_RESPONSE, failure="private-failure-marker"))
    await BudgetedWebSearchGateway(gateway, ledger.budget()).search("test", "luna", WEB_REQUEST)
    assert ledger.payload["calls"][0]["error"] == "provider_error"
    assert "private-" not in json.dumps(ledger.payload)


async def test_web_exception_keeps_full_reservation():
    ledger = Ledger()
    gateway = Gateway(ledger)
    gateway.error = WebSearchError("private-failure-marker")
    with pytest.raises(WebSearchError):
        await BudgetedWebSearchGateway(gateway, ledger.budget()).search("test", "luna", WEB_REQUEST)
    assert output_used(ledger.payload) == 16000
    assert "private-" not in json.dumps(ledger.payload)


async def test_optional_profile_is_not_fabricated():
    ledger = Ledger()
    wrapped = BudgetedLlmGateway(Gateway(ledger), ReportCallBudget(ledger.mutate, ledger.check))
    await wrapped.complete("https://model.example", "test", "luna", REQUEST)
    assert ledger.payload["calls"][0]["profile_id"] is None


async def test_allowance_gateway_reserves_input_and_output_then_settles_actual_usage():
    accounting = FakeAccounting()
    attribution = AiAttribution.actor(uuid4(), uuid4())
    wrapped = AllowanceLlmGateway(
        RawGateway(), accounting, attribution=attribution, profile_id=uuid4()
    )
    result = await wrapped.complete("https://model.example", "secret", "luna", REQUEST)
    assert result.completion_tokens == 34
    assert accounting.reserved[0][0] == attribution
    assert accounting.reserved[0][1]["requested_tokens"] > REQUEST.max_output_tokens
    assert len(accounting.dispatched) == 1
    assert accounting.finished == [
        (
            AiCallOutcome.COMPLETED,
            {"prompt_tokens": 12, "completion_tokens": 34, "error": None},
        )
    ]


async def test_allowance_gateway_settles_failed_provider_call_without_leaking_error_text():
    accounting = FakeAccounting()
    wrapped = AllowanceLlmGateway(
        RawGateway(error=RuntimeError("private-provider-response")),
        accounting,
        attribution=AiAttribution.actor(uuid4()),
        profile_id=uuid4(),
    )
    with pytest.raises(RuntimeError, match="private-provider-response"):
        await wrapped.complete("https://model.example", "secret", "luna", REQUEST)
    assert accounting.finished[0][0] is AiCallOutcome.FAILED
    assert accounting.finished[0][1]["error"] == "provider_error"


async def test_unrecorded_dispatch_is_never_sent_and_is_released():
    accounting = FakeAccounting()
    accounting.dispatch_error = OSError("storage unavailable")
    raw = RawGateway()
    raw.calls = 0
    wrapped = AllowanceLlmGateway(
        raw, accounting, attribution=AiAttribution.actor(uuid4()), profile_id=None
    )
    with pytest.raises(CallNotDispatched):
        await wrapped.complete("https://model.example", "secret", "luna", REQUEST)
    assert accounting.finished[0][0] is AiCallOutcome.NOT_DISPATCHED


async def test_allowance_refusal_inside_job_budget_is_recorded_as_not_dispatched():
    ledger = Ledger()
    accounting = FakeAccounting(reserve_error=AiAllowanceExceeded())
    inner = AllowanceLlmGateway(
        Gateway(ledger), accounting, attribution=AiAttribution.actor(uuid4()), profile_id=None
    )
    with pytest.raises(AiAllowanceExceeded):
        await BudgetedLlmGateway(inner, ledger.budget()).complete(
            "https://model.example", "test", "luna", REQUEST
        )
    [entry] = ledger.payload["calls"]
    assert (entry["status"], entry["error"]) == ("failed", "not_dispatched")
    assert output_used(ledger.payload) == 0
