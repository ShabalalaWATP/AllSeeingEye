"""Do not pay for an identical report retry after explicit native token exhaustion."""

import json
from dataclasses import replace

import httpx
import pytest

from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway
from ase.adapters.llm.openai_responses import parse_response
from ase.application.ports.llm import LlmGatewayError, LlmTokenBudgetExhausted
from ase.application.reports import drafting
from ase.application.reports.drafting import draft_body
from ase.application.reports.production import Producer
from ase.application.reports.templates import TEMPLATES
from ase.domain.evidence import quality_of_information
from ase.domain.llm import ReasoningEffort
from ase.domain.reports import ReportHeader, ReportStatus
from feeds_helpers import NOW
from production_integration_helpers import RecordingUsage, production_job
from report_helpers import filled_store
from test_openai_responses import BASE, response_data
from test_report_integrity import evidence, sound_body


def exhausted():
    data = response_data()
    data.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"})
    data["usage"] = {"input_tokens": 1234, "output_tokens": 32000}
    data["output"] = [{"type": "reasoning", "content": "private-output-marker"}]
    data["error"] = {"message": "private-error-marker"}
    return data


def test_explicit_exhaustion_carries_only_validated_accounting_and_safe_error():
    with pytest.raises(LlmTokenBudgetExhausted) as caught:
        parse_response(exhausted(), "fallback", 0)
    error = caught.value
    assert error.model == "gpt-5.6-luna-returned"
    assert (error.prompt_tokens, error.completion_tokens) == (1234, 32000)
    assert "private" not in str(error) and "private" not in repr(vars(error))


@pytest.mark.parametrize(
    "usage",
    [
        None,
        [],
        "private",
        {"input_tokens": True},
        {"input_tokens": -1},
        {"input_tokens": 2**63},
        {"input_tokens": "private", "output_tokens": False},
    ],
)
def test_bad_optional_usage_cannot_trigger_same_budget_retry_or_fabricate_counts(usage):
    data = exhausted()
    data.update(usage=usage, model="invalid\nprivate-model-marker")
    with pytest.raises(LlmTokenBudgetExhausted) as caught:
        parse_response(data, "fallback", 0)
    assert caught.value.model == ""
    assert caught.value.prompt_tokens is None and caught.value.completion_tokens is None
    assert "private" not in str(caught.value) and "private" not in repr(vars(caught.value))


def test_exhaustion_can_retain_one_known_count_without_inventing_the_other():
    data = exhausted()
    data.pop("model")
    data["usage"] = {"input_tokens": False, "output_tokens": 32000}
    with pytest.raises(LlmTokenBudgetExhausted) as caught:
        parse_response(data, "configured-model", 0)
    assert caught.value.model == "configured-model"
    assert caught.value.prompt_tokens is None and caught.value.completion_tokens == 32000


@pytest.mark.parametrize(
    "details", [None, [], {}, {"reason": "content_filter"}, {"reason": "private unknown reason"}]
)
def test_only_explicit_native_max_output_reason_gets_non_retryable_classification(details):
    data = exhausted()
    data["incomplete_details"] = details
    with pytest.raises(LlmGatewayError) as caught:
        parse_response(data, "fallback", 0)
    assert not isinstance(caught.value, LlmTokenBudgetExhausted)
    assert "private" not in str(caught.value)


async def make_draft(client, container, user):
    profile = replace(
        production_job(user, container.cipher).profile,
        base_url=BASE,
        model="gpt-5.6-luna",
        reasoning_effort=ReasoningEffort.MAX,
        max_output_tokens=32000,
    )
    return await draft_body(
        OpenAiCompatibleGateway(client=client),
        profile,
        "private-key-marker",
        TEMPLATES["intsum"],
        ReportHeader("intsum", "Fixture", {}, NOW, NOW, NOW),
        None,
        quality_of_information(evidence()),
        evidence(),
        (),
    )


async def test_native_exhaustion_stops_after_one_call_and_keeps_costs(container, user, monkeypatch):
    calls = []
    elapsed = 0.0

    def handler(request):
        nonlocal elapsed
        calls.append(request)
        elapsed = 2.5
        return httpx.Response(200, json=exhausted())

    monkeypatch.setattr(drafting.time, "perf_counter", lambda: elapsed)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        draft = await make_draft(client, container, user)
    assert len(calls) == draft.attempts == 1
    assert draft.body is None and draft.has_errors
    assert (draft.prompt_tokens, draft.completion_tokens) == (1234, 32000)
    assert draft.model == "gpt-5.6-luna-returned" and draft.latency_ms == 2500
    assert "private" not in str(draft.findings)
    payload = json.loads(calls[0].content)
    assert payload["max_output_tokens"] == 32000 and payload["reasoning"]["effort"] == "max"


async def test_unknown_failure_usage_remains_unknown_in_draft(container, user):
    data = exhausted()
    data.pop("usage")
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=data))
    ) as client:
        draft = await make_draft(client, container, user)
    assert draft.attempts == 1 and draft.body is None
    assert draft.prompt_tokens is None and draft.completion_tokens is None
    assert 0 <= draft.latency_ms < 10_000


@pytest.mark.parametrize("first", ["transient", "invalid-json", "validation", "then-exhausted"])
async def test_transient_and_validation_repairs_keep_existing_retry(container, user, first):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1 and first == "transient":
            return httpx.Response(503, text="private-upstream-marker")
        data = response_data()
        body = sound_body()
        if len(calls) == 1 and first in {"validation", "then-exhausted"}:
            body["key_judgements"][0]["supporting_evidence"] = ["invented"]
        data["output"][1]["content"][0]["text"] = (
            "not-json" if len(calls) == 1 and first == "invalid-json" else json.dumps(body)
        )
        if len(calls) == 2 and first == "then-exhausted":
            data = exhausted()
        return httpx.Response(200, json=data)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        draft = await make_draft(client, container, user)
    assert len(calls) == draft.attempts == 2
    if first == "then-exhausted":
        assert draft.body is None and draft.has_errors
        assert (draft.prompt_tokens, draft.completion_tokens) == (1275, 32090)
    else:
        assert draft.body is not None and not draft.has_errors


async def test_failure_usage_reaches_normal_production_records(container, user):
    usage = RecordingUsage()
    job = production_job(user, container.cipher)
    job = replace(
        job,
        profile=replace(
            job.profile,
            base_url=BASE,
            model="gpt-5.6-luna",
            reasoning_effort=ReasoningEffort.MAX,
            max_output_tokens=32000,
        ),
    )

    async def profile_for(role):
        return None

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=exhausted()))
    ) as client:
        producer = Producer(
            store=filled_store(),
            source_profiles={},
            cipher=container.cipher,
            gateway=OpenAiCompatibleGateway(client=client),
            usage=usage,
        )
        version = await producer.produce(job, profile_for)
    assert version.status is ReportStatus.FAILED and version.attempts == 1
    assert (version.prompt_tokens, version.completion_tokens) == (1234, 32000)
    assert len(usage.rows) == 1 and not usage.rows[0].ok
    assert (usage.rows[0].prompt_tokens, usage.rows[0].completion_tokens) == (1234, 32000)
