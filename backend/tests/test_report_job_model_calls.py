"""The budget wrapper preserves all model controls and fingerprints complete requests."""

import json
from dataclasses import replace

import pytest

from ase.application.ports.llm import LlmTokenBudgetExhausted
from ase.application.ports.web_search import WebSearchError, WebSearchRequest, WebSearchResult
from ase.application.report_jobs.budget import ReportCallBudget, output_used
from ase.application.report_jobs.model_calls import BudgetedLlmGateway, BudgetedWebSearchGateway
from ase.domain.errors import InvalidRequest
from ase.domain.llm import LlmImage, LlmMessage, LlmProvider, ReasoningEffort
from report_job_budget_helpers import REQUEST, Gateway, Ledger
from test_report_job_budget import call

WEB_REQUEST = WebSearchRequest("private-query-marker", 16000, ReasoningEffort.MAX)
WEB_RESPONSE = WebSearchResult("private-output-marker", (), (), "luna", 1, 4, 100, 200)


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
