"""Native Converse payload, schema and response contracts against synthetic AWS replies."""

import asyncio
import json
from copy import deepcopy
from dataclasses import replace

import httpx
import pytest

from ase.adapters.llm import bedrock
from ase.adapters.llm.bedrock import BedrockConverseGateway, build_payload, parse_response
from ase.adapters.llm.bedrock_schema import project_schema
from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway
from ase.adapters.llm.router import RoutingLlmGateway
from ase.application.ports.llm import LlmGatewayError
from ase.application.reports.challenge_models import PLAN_SCHEMA, REVIEW_SCHEMA
from ase.domain.advocacy import ADVOCACY_SCHEMA
from ase.domain.direction import DIRECTION_SCHEMA
from ase.domain.llm import LlmMessage, LlmProvider, LlmRequest, ReasoningEffort
from ase.domain.report_schema import REPORT_BODY_SCHEMA

BASE = "https://bedrock-runtime.us-east-1.amazonaws.com"
MODEL = "openai.gpt-oss-120b-1:0"
REQUEST = LlmRequest(
    (LlmMessage("system", "System fixture"), LlmMessage("user", "Private fixture")),
    2000,
    0.1,
    REPORT_BODY_SCHEMA,
    "report",
    provider=LlmProvider.BEDROCK,
)


def answer() -> dict:
    return {
        "stopReason": "end_turn",
        "output": {"message": {"role": "assistant", "content": [{"text": '{"ok":true}'}]}},
        "usage": {"inputTokens": 30, "outputTokens": 10, "totalTokens": 40},
    }


@pytest.mark.parametrize(
    "schema", [REPORT_BODY_SCHEMA, DIRECTION_SCHEMA, ADVOCACY_SCHEMA, PLAN_SCHEMA, REVIEW_SCHEMA]
)
def test_real_stage_schemas_project_without_modifying_local_constraints(schema: dict) -> None:
    original = deepcopy(schema)
    projected = project_schema(schema)
    encoded = json.dumps(projected)
    assert '"maxLength"' not in encoded and '"minLength"' not in encoded
    assert '"maxItems"' not in encoded
    assert projected["required"] == schema["required"]
    assert projected["additionalProperties"] is False
    assert schema == original
    if schema is REPORT_BODY_SCHEMA:
        assert '"maxLength"' in json.dumps(schema)


def test_schema_property_names_and_constraints_do_not_get_confused() -> None:
    schema = {
        "type": "object",
        "properties": {
            "minimum": {"type": "integer", "minimum": 1},
            "minLength": {"type": "array", "minItems": 2, "items": {"type": "string"}},
        },
    }
    projected = project_schema(schema)
    assert projected["properties"]["minimum"] == {"type": "integer"}
    assert "minItems" not in projected["properties"]["minLength"]
    with pytest.raises(LlmGatewayError, match="references"):
        project_schema({"$ref": "https://untrusted.invalid/schema"})
    with pytest.raises(LlmGatewayError, match="references"):
        project_schema(
            {"$ref": "#/$defs/recursive", "$defs": {"recursive": {"$ref": "#/$defs/recursive"}}}
        )
    for value in (True, {"type": "string"}):
        with pytest.raises(LlmGatewayError, match="additionalProperties"):
            project_schema({"type": "object", "additionalProperties": value})
    recursive = {}
    recursive["items"] = recursive
    with pytest.raises(LlmGatewayError, match="bounds"):
        project_schema(recursive)


async def test_native_payload_uses_safe_endpoint_encoded_id_and_explicit_bearer() -> None:
    model = "arn:aws:bedrock:us-east-1:123456789012:inference-profile/fixture"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.raw_path.endswith(b"inference-profile%2Ffixture/converse")
        assert request.headers["authorization"] == "Bearer selected-key"
        assert request.headers["accept-encoding"] == "identity"
        payload = json.loads(request.content)
        assert payload["system"] == [{"text": "System fixture"}]
        assert payload["messages"] == [{"role": "user", "content": [{"text": "Private fixture"}]}]
        assert payload["inferenceConfig"] == {"maxTokens": 2000, "temperature": 0.1}
        config = payload["outputConfig"]["textFormat"]
        assert config["type"] == "json_schema"
        assert config["structure"]["jsonSchema"]["name"] == "report"
        assert (
            json.loads(config["structure"]["jsonSchema"]["schema"])["required"]
            == REPORT_BODY_SCHEMA["required"]
        )
        return httpx.Response(200, json=answer())

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        auth=("inherited", "password"),
        headers={"Authorization": "Bearer wrong-key"},
    ) as client:
        result = await BedrockConverseGateway(client=client).complete(
            BASE, "selected-key", model, REQUEST
        )
    assert result.content == '{"ok":true}' and result.model == model
    assert result.prompt_tokens == 30 and result.completion_tokens == 10


@pytest.mark.parametrize(
    "stop",
    [None, "max_tokens", "guardrail_intervened", "content_filtered", "tool_use", "stop_sequence"],
)
def test_only_complete_unblocked_responses_are_accepted(stop: str | None) -> None:
    data = answer()
    data["stopReason"] = stop
    with pytest.raises(LlmGatewayError):
        parse_response(data, MODEL, 1)


@pytest.mark.parametrize("value", [None, True, -1, "30", 1_000_000_001])
def test_invalid_token_usage_is_rejected(value: object) -> None:
    data = answer()
    data["usage"]["inputTokens"] = value
    with pytest.raises(LlmGatewayError, match="usage"):
        parse_response(data, MODEL, 1)


def test_reasoning_is_discarded_and_nontext_refusal_blocks_are_rejected() -> None:
    data = answer()
    blocks = data["output"]["message"]["content"]
    blocks.insert(
        0,
        {
            "reasoningContent": {
                "reasoningText": {"text": "private-thought", "signature": "private-signature"}
            }
        },
    )
    blocks.insert(0, {"reasoningContent": {"redactedContent": "YQ=="}})
    assert parse_response(data, MODEL, 1).content == '{"ok":true}'
    blocks.append({"refusal": "Sensitive refusal fixture"})
    with pytest.raises(LlmGatewayError, match="unsupported or refused"):
        parse_response(data, MODEL, 1)
    with pytest.raises(LlmGatewayError, match="empty"):
        parse_response(
            {**answer(), "output": {"message": {"role": "assistant", "content": [{"text": " "}]}}},
            MODEL,
            1,
        )


@pytest.mark.parametrize(
    "change",
    [
        {"reasoning_effort": ReasoningEffort.MAX},
        {"temperature": 1.5},
        {"max_output_tokens": 0},
    ],
)
def test_unsupported_inference_settings_fail_before_http(change: dict) -> None:
    with pytest.raises(LlmGatewayError):
        build_payload(replace(REQUEST, **change))


@pytest.mark.parametrize(
    "base,key,model",
    [
        ("https://example.invalid", "key", MODEL),
        (BASE + "/openai/v1", "key", MODEL),
        (BASE, "", MODEL),
        (BASE, "key\n", MODEL),
        (BASE, "key", ".."),
    ],
)
async def test_invalid_boundary_values_never_send(base: str, key: str, model: str) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: pytest.fail("No HTTP"))
    ) as client:
        with pytest.raises(LlmGatewayError):
            await BedrockConverseGateway(client=client).complete(base, key, model, REQUEST)


@pytest.mark.parametrize("kind", ["redirect", "error", "compressed", "size", "deep", "json"])
async def test_untrusted_http_is_bounded_and_never_echoed(
    kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if kind == "redirect":
            return httpx.Response(302, headers={"Location": "https://other.invalid"})
        if kind == "error":
            return httpx.Response(400, text="secret-marker")
        if kind == "compressed":
            return httpx.Response(200, headers={"Content-Encoding": "gzip"})
        if kind == "size":
            return httpx.Response(200, content=b" " * 17)
        if kind == "deep":
            return httpx.Response(200, content=b"[" * 66 + b"0" + b"]" * 66)
        return httpx.Response(200, content=b"secret-marker")

    if kind == "size":
        monkeypatch.setattr(bedrock, "MAX_RESPONSE_BYTES", 16)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as client:
        with pytest.raises(LlmGatewayError) as error:
            await BedrockConverseGateway(client=client).complete(BASE, "key", MODEL, REQUEST)
    assert "secret-marker" not in str(error.value) and len(calls) == 1


async def test_total_deadline_and_two_request_admission() -> None:
    active = maximum = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active, maximum
        active += 1
        maximum = max(active, maximum)
        try:
            await asyncio.sleep(0.08)
            return httpx.Response(200, json=answer())
        finally:
            active -= 1

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = BedrockConverseGateway(client=client, timeout_seconds=0.12)
        results = await asyncio.gather(
            *(gateway.complete(BASE, "key", MODEL, REQUEST) for _ in range(3)),
            return_exceptions=True,
        )
    assert maximum == 2 and active == 0
    assert sum(isinstance(result, LlmGatewayError) for result in results) == 1


async def test_router_dispatches_exact_provider_without_fallback_and_closes_clients() -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if request.url.path.endswith("converse"):
            return httpx.Response(400, text="AWS failure")
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    openai_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    bedrock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    router = RoutingLlmGateway(
        OpenAiCompatibleGateway(client=openai_client), BedrockConverseGateway(client=bedrock_client)
    )
    with pytest.raises(LlmGatewayError):
        await router.complete(BASE, "key", MODEL, REQUEST)
    assert len(seen) == 1
    result = await router.complete(
        "http://localhost/v1", "", "local", replace(REQUEST, provider=LlmProvider.OPENAI_COMPATIBLE)
    )
    assert result.content == "ok" and len(seen) == 2
    with pytest.raises(LlmGatewayError, match="unsupported"):
        await router.complete(BASE, "key", MODEL, replace(REQUEST, provider="unknown"))
    assert len(seen) == 2
    await router.aclose()
    assert openai_client.is_closed and bedrock_client.is_closed
