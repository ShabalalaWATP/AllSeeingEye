"""Actual outbound Luna parameters and bounded discovery without real network calls."""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from evaluations.casebook import load_cases
from evaluations.pipeline import EvaluationProfile, RecordingGateway, evaluate_case

from ase.adapters.llm import model_discovery
from ase.adapters.llm.openai_compatible import (
    OpenAiCompatibleGateway,
    build_payload,
    parse_completion,
)
from ase.adapters.llm.translator import translation_request
from ase.application.ports.llm import LlmGatewayError
from ase.domain.llm import LlmMessage, LlmProfile, LlmRequest, LlmRole, ReasoningEffort
from evaluation_helpers import EvaluationGateway

BASE = "https://api.openai.com/v1"
REQUEST = LlmRequest((LlmMessage("user", "Fixture"),), 16000, 0, reasoning_effort="max")


async def test_luna_max_outbound_payload_preserves_model_and_combined_budget() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == BASE + "/responses"
        assert request.headers["authorization"] == "Bearer fixture-secret"
        body = json.loads(request.content)
        assert body["model"] == "gpt-5.6-luna"
        assert body["reasoning"] == {"effort": "max"}
        assert body["max_output_tokens"] == 16000 and body["store"] is False
        assert "max_tokens" not in body and "temperature" not in body
        return httpx.Response(
            200,
            json={
                "model": "gpt-5.6-luna",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [{"type": "output_text", "text": '{"ok":true}'}],
                    }
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAiCompatibleGateway(client=client).complete(
            BASE,
            "fixture-secret",
            "gpt-5.6-luna",
            REQUEST,
        )
    assert result.model == "gpt-5.6-luna"


async def test_completion_does_not_inherit_client_credentials() -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["authorization"])
        if request.url.path.endswith("/responses"):
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "role": "assistant",
                            "status": "completed",
                            "content": [{"type": "output_text", "text": "ok"}],
                        }
                    ],
                },
            )
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer inherited-secret"},
        auth=("inherited-user", "inherited-password"),
    ) as client:
        gateway = OpenAiCompatibleGateway(client=client)
        await gateway.complete(BASE, "selected-secret", "gpt-5.6-luna", REQUEST)
        await gateway.complete("http://localhost:11434/v1", "", "local-model", REQUEST)
    assert seen == ["Bearer selected-secret", ""]


def test_legacy_payload_stays_compatible_and_luna_default_uses_modern_budget() -> None:
    request = replace(REQUEST, reasoning_effort=None)
    legacy = build_payload("local-llama", request)
    assert legacy["temperature"] == 0 and legacy["max_tokens"] == 16000
    assert "reasoning_effort" not in legacy and "max_completion_tokens" not in legacy
    luna = build_payload("gpt-5.6-luna", request)
    assert luna["max_completion_tokens"] == 16000
    assert "temperature" not in luna and "reasoning_effort" not in luna


def test_truncated_but_plausible_json_is_not_accepted_as_finished() -> None:
    with pytest.raises(LlmGatewayError, match="token budget"):
        parse_completion(
            {"choices": [{"message": {"content": '{"ok":true}'}, "finish_reason": "length"}]},
            "gpt-5.6-luna",
            1,
        )


async def test_discovery_sorts_deduplicates_and_does_not_inherit_credentials() -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        assert request.method == "GET" and str(request.url) == BASE + "/models"
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(
            200,
            json={"data": [{"id": "local-model"}, {"id": "gpt-5.6-luna"}, {"id": "local-model"}]},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer inherited"},
        auth=("inherited-user", "inherited-secret"),
    ) as client:
        gateway = OpenAiCompatibleGateway(client=client)
        assert await gateway.list_models(BASE, "fixture-secret") == ("gpt-5.6-luna", "local-model")
        assert await gateway.list_models(BASE, "") == ("gpt-5.6-luna", "local-model")
    assert seen[0].headers["authorization"] == "Bearer fixture-secret"
    assert seen[1].headers["authorization"] == ""


@pytest.mark.parametrize("fault", ["redirect", "status", "gzip", "json", "id", "count", "depth"])
async def test_discovery_rejects_untrusted_responses_without_echoing_body(fault: str) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:  # noqa: PLR0911
        nonlocal calls
        calls += 1
        if fault == "redirect":
            return httpx.Response(302, headers={"Location": "https://other.invalid/steal"})
        if fault == "status":
            return httpx.Response(401, text="secret-error-marker")
        if fault == "gzip":
            return httpx.Response(200, headers={"Content-Encoding": "gzip"})
        if fault == "json":
            return httpx.Response(200, text="secret-error-marker")
        if fault == "id":
            return httpx.Response(200, json={"data": [{"id": "secret-error-marker\n"}]})
        if fault == "count":
            return httpx.Response(200, json={"data": [{"id": "a"}] * 1001})
        return httpx.Response(
            200, content=b'{"data":[],"extra":' + b"[" * 70 + b"0" + b"]" * 70 + b"}"
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as client:
        with pytest.raises(LlmGatewayError) as error:
            await OpenAiCompatibleGateway(client=client).list_models(BASE, "fixture-secret")
    assert "secret-error-marker" not in str(error.value)
    assert "fixture-secret" not in str(error.value)
    assert calls == 1


async def test_discovery_enforces_size_and_total_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(model_discovery, "MAX_DISCOVERY_BYTES", 16)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b" " * 17),
        )
    ) as client:
        with pytest.raises(LlmGatewayError, match="size limit"):
            await OpenAiCompatibleGateway(client=client).list_models(BASE, "")

    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(1)
        return httpx.Response(200, json={"data": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(slow)) as client:
        with pytest.raises(LlmGatewayError, match="timed out"):
            await OpenAiCompatibleGateway(client=client, timeout_seconds=0.01).list_models(BASE, "")


def test_translation_preserves_max_effort_and_combined_budget() -> None:
    now = datetime.now(UTC)
    profile = LlmProfile(
        uuid4(),
        "Luna",
        BASE,
        "gpt-5.6-luna",
        "",
        "",
        frozenset({LlmRole.TRANSLATION}),
        16000,
        0,
        True,
        now,
        now,
        reasoning_effort=ReasoningEffort.MAX,
    )
    request = translation_request([("Bonjour", "fr")], profile)
    assert request.reasoning_effort == "max"
    assert request.max_output_tokens == 16000
    assert (
        translation_request(
            [("Bonjour", "fr")], replace(profile, reasoning_effort=None, model="legacy-local")
        ).max_output_tokens
        == 4000
    )


async def test_legacy_advocacy_also_receives_selected_effort_and_budget() -> None:
    gateway = RecordingGateway(EvaluationGateway(), 6)
    configuration = EvaluationProfile(
        base_url=BASE,
        model="gpt-5.6-luna",
        direction=True,
        advocacy=True,
        reasoning_effort=ReasoningEffort.MAX,
        max_output_tokens=16000,
    )
    await evaluate_case(load_cases()[0], configuration, gateway, "")
    assert {record["schema_name"] for record in gateway.records} == {
        "direction",
        "report",
        "advocacy",
        "report_analysis",
        "entailment",
    }
    assert all(record["reasoning_effort"] == "max" for record in gateway.records)
    assert all(record["max_output_tokens"] == 16000 for record in gateway.records)
