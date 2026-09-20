"""Provider substitution must not repeat an explicitly exhausted output budget."""

from dataclasses import replace

import httpx
import pytest

from ase.adapters.llm.bedrock import BedrockConverseGateway
from ase.adapters.llm.bedrock import parse_response as parse_bedrock
from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway, parse_completion
from ase.adapters.llm.openai_responses import parse_response
from ase.application.ports.llm import LlmGatewayError, LlmTokenBudgetExhausted
from ase.application.reports.drafting import draft_body
from ase.application.reports.templates import TEMPLATES
from ase.domain.evidence import quality_of_information
from ase.domain.llm import LlmProvider, ReasoningEffort
from ase.domain.reports import ReportHeader
from feeds_helpers import NOW
from production_integration_helpers import production_job
from test_report_integrity import evidence

PROVIDERS = ("responses", "chat", "bedrock")
PARSERS = {"responses": parse_response, "chat": parse_completion, "bedrock": parse_bedrock}
USAGE_KEYS = {
    "responses": ("input_tokens", "output_tokens"),
    "chat": ("prompt_tokens", "completion_tokens"),
    "bedrock": ("inputTokens", "outputTokens"),
}


def exhausted(provider, prompt=123, completion=32000):
    data = {
        "model": "configured-model",
        "usage": dict(zip(USAGE_KEYS[provider], (prompt, completion), strict=True)),
        "error": {"message": "private-error-marker"},
    }
    if provider == "responses":
        data.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"})
        data["output"] = [{"content": "private-output-marker"}]
    elif provider == "chat":
        data["choices"] = [
            {"finish_reason": "length", "message": {"content": "private-output-marker"}}
        ]
    else:
        data.update(stopReason="max_tokens", output={"content": "private-output-marker"})
    return data


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("bad", [None, True, -1, 2**31, "private", 1.5])
def test_explicit_exhaustion_is_terminal_even_with_invalid_optional_usage(provider, bad):
    with pytest.raises(LlmTokenBudgetExhausted) as caught:
        PARSERS[provider](exhausted(provider, prompt=bad), "configured-model", 0)
    assert caught.value.prompt_tokens is None
    assert caught.value.completion_tokens == 32000
    assert caught.value.model == "configured-model"
    assert "private" not in str(caught.value) + repr(vars(caught.value))


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("usage", [None, [], "private-usage-marker"])
def test_malformed_usage_and_model_do_not_leak_or_change_terminal_outcome(provider, usage):
    data = exhausted(provider)
    data.update(usage=usage, model="invalid\nprivate-model-marker")
    with pytest.raises(LlmTokenBudgetExhausted) as caught:
        PARSERS[provider](data, "invalid\nprivate-model-marker", 0)
    assert caught.value.model == ""
    assert caught.value.prompt_tokens is None and caught.value.completion_tokens is None
    assert "private" not in str(caught.value) + repr(vars(caught.value))


def test_bedrock_exhaustion_retains_supported_long_profile_identifier():
    model = "arn:aws:bedrock:us-east-1:123456789012:inference-profile/" + "x" * 150
    with pytest.raises(LlmTokenBudgetExhausted) as caught:
        parse_bedrock(exhausted("bedrock"), model, 0)
    assert caught.value.model == model


@pytest.mark.parametrize("provider", PROVIDERS)
async def test_real_gateway_drafting_contract_stops_after_one_request(provider, container, user):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=exhausted(provider))

    profile = replace(
        production_job(user, container.cipher).profile,
        base_url=(
            "https://bedrock-runtime.us-east-1.amazonaws.com"
            if provider == "bedrock"
            else "https://api.openai.com/v1"
        ),
        provider=LlmProvider.BEDROCK if provider == "bedrock" else LlmProvider.OPENAI_COMPATIBLE,
        model="configured-model",
        reasoning_effort=ReasoningEffort.MAX if provider == "responses" else None,
        max_output_tokens=32000,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = (
            BedrockConverseGateway(client=client)
            if provider == "bedrock"
            else OpenAiCompatibleGateway(client=client)
        )
        draft = await draft_body(
            gateway,
            profile,
            "fixture-key",
            TEMPLATES["intsum"],
            ReportHeader("intsum", "Fixture", {}, NOW, NOW, NOW),
            None,
            quality_of_information(evidence()),
            evidence(),
            (),
        )
    assert len(calls) == draft.attempts == 1
    assert draft.body is None and draft.has_errors
    assert (draft.prompt_tokens, draft.completion_tokens) == (123, 32000)
    assert "private" not in str(draft.findings)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_unknown_stop_reason_is_not_classified_as_explicit_exhaustion(provider):
    data = exhausted(provider)
    if provider == "responses":
        data["incomplete_details"] = {"reason": "unknown"}
    elif provider == "chat":
        data["choices"] = [{"finish_reason": "unknown"}]
    else:
        data["stopReason"] = "unknown"
    with pytest.raises(LlmGatewayError) as caught:
        PARSERS[provider](data, "configured-model", 0)
    assert not isinstance(caught.value, LlmTokenBudgetExhausted)
