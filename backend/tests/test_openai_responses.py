"""Official max reasoning uses Responses without weakening the shared transport boundary."""

import asyncio
import base64
import json
from copy import deepcopy
from dataclasses import replace

import httpx
import pytest

from ase.adapters.llm import openai_compatible
from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway
from ase.adapters.llm.openai_responses import build_responses_payload, parse_response
from ase.application.ports.llm import LlmGatewayError
from ase.domain.llm import LlmImage, LlmMessage, LlmRequest
from test_llm_gateway_security import RecordingStream
from test_photo_geolocation_contracts import PNG

BASE = "https://api.openai.com/v1"
SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}
REQUEST = LlmRequest(
    (LlmMessage("system", "Return the requested format."), LlmMessage("user", "Check connection.")),
    16000,
    0.2,
    json_schema=SCHEMA,
    schema_name="connection_test",
    reasoning_effort="max",
)


def response_data():
    return {
        "status": "completed",
        "model": "gpt-5.6-luna-returned",
        "output": [
            {"type": "reasoning", "summary": []},
            {
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": '{"ok":true}', "annotations": []}],
            },
        ],
        "usage": {
            "input_tokens": 41,
            "output_tokens": 90,
            "output_tokens_details": {"reasoning_tokens": 80},
        },
    }


async def test_official_max_preserves_schema_messages_budget_usage_and_selected_credential():
    def handler(request):
        assert str(request.url) == BASE + "/responses"
        assert request.headers["authorization"] == "Bearer selected-fixture"
        assert request.headers["accept-encoding"] == "identity"
        body = json.loads(request.content)
        assert body == {
            "model": "gpt-5.6-luna",
            "input": [
                {"role": "system", "content": "Return the requested format."},
                {"role": "user", "content": "Check connection."},
            ],
            "reasoning": {"effort": "max"},
            "max_output_tokens": 16000,
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "connection_test",
                    "strict": True,
                    "schema": SCHEMA,
                }
            },
        }
        assert "selected-fixture" not in request.content.decode()
        return httpx.Response(200, json=response_data())

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer inherited"},
        auth=("inherited", "password"),
    ) as client:
        result = await OpenAiCompatibleGateway(client=client).complete(
            BASE, "selected-fixture", "gpt-5.6-luna", REQUEST
        )
    assert result.content == '{"ok":true}' and result.model == "gpt-5.6-luna-returned"
    assert result.prompt_tokens == 41 and result.completion_tokens == 90
    assert result.latency_ms >= 0


async def test_sanitised_image_uses_native_input_image_and_high_detail():
    def handler(request):
        content = json.loads(request.content)["input"][1]["content"]
        assert content[0] == {"type": "input_text", "text": "Find scene clues."}
        assert content[1]["type"] == "input_image" and content[1]["detail"] == "high"
        assert content[1]["image_url"].startswith("data:image/png;base64,")
        assert base64.b64decode(content[1]["image_url"].split(",", 1)[1]) == PNG
        return httpx.Response(200, json=response_data())

    request = replace(
        REQUEST,
        messages=(REQUEST.messages[0], LlmMessage("user", "Find scene clues.", (LlmImage(PNG),))),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAiCompatibleGateway(client=client).complete(
            BASE, "fixture", "vision", request
        )
    assert result.content == '{"ok":true}'


@pytest.mark.parametrize(
    "base,effort",
    [
        (BASE, None),
        (BASE, "xhigh"),
        ("http://localhost:11434/v1", "max"),
        ("https://api.openai.com.proxy.example/v1", "max"),
        ("https://api.openai.com/v1/custom", "max"),
        ("https://api.openai.com:443/v1", "max"),
    ],
)
async def test_other_endpoints_and_non_max_keep_chat_compatibility(base, effort):
    def handler(request):
        assert request.url == httpx.URL(base + "/chat/completions")
        body = json.loads(request.content)
        assert body["model"] == "configured-model"
        assert body.get("reasoning_effort") == effort and "input" not in body
        assert body["response_format"]["json_schema"]["strict"] is True
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAiCompatibleGateway(client=client).complete(
            base, "fixture", "configured-model", replace(REQUEST, reasoning_effort=effort)
        )
    assert result.content == "ok"


@pytest.mark.parametrize(
    "path,value",
    [
        (("status",), "incomplete"),
        (("status",), "failed"),
        (("status",), None),
        (("error",), {"message": "private upstream error"}),
        (("output", 1, "content"), [{"type": "refusal", "refusal": "private refusal content"}]),
        (("output", 1, "status"), "incomplete"),
        (("output", 1, "role"), "user"),
        (("output",), []),
        (("output", 1, "content"), []),
        (("output", 1, "content"), None),
        (("output", 1, "content", 0, "text"), {}),
        (("output", 1, "type"), "function_call"),
        (("output",), [{"type": "reasoning", "summary": []}]),
        (("output",), "untrusted"),
        (("output", 1), "untrusted"),
        (("usage",), []),
        (("usage", "input_tokens"), -1),
        (("usage", "output_tokens"), True),
        (("usage", "input_tokens"), 2_147_483_648),
        (("model",), "invalid model"),
        (("output", 1, "content", 0, "text"), " "),
    ],
)
def test_native_response_rejects_unfinished_refused_and_malformed_bodies(path, value):
    data = deepcopy(response_data())
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(LlmGatewayError) as error:
        parse_response(data, "fallback", 1)
    assert "private" not in str(error.value)


def test_unstructured_multi_part_answer_and_optional_usage_remain_supported():
    data = response_data()
    data["output"][1]["content"] = [
        {"type": "output_text", "text": "Part one."},
        {"type": "output_text", "text": " Part two."},
    ]
    data.pop("model")
    data.pop("usage")
    result = parse_response(data, "configured-model", 10)
    assert result.content == "Part one. Part two." and result.model == "configured-model"
    assert result.prompt_tokens is None and result.completion_tokens is None
    payload = build_responses_payload("configured-model", replace(REQUEST, json_schema=None))
    assert "text" not in payload and payload["store"] is False


@pytest.mark.parametrize("data", [None, [], "untrusted"])
def test_non_object_response_envelopes_fail_closed(data):
    with pytest.raises(LlmGatewayError, match="other than an object"):
        parse_response(data, "fallback", 0)


@pytest.mark.parametrize("status", [302, 400, 401, 429, 503])
async def test_native_status_failure_never_retries_changes_model_or_echoes_body(status):
    seen = []
    stream = RecordingStream([b"private-key private query private upstream error"])

    def handler(request):
        seen.append(request)
        return httpx.Response(status, stream=stream, headers={"Location": "https://other.example"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as client:
        with pytest.raises(LlmGatewayError) as error:
            await OpenAiCompatibleGateway(client=client).complete(
                BASE, "private-key", "model", REQUEST
            )
    assert str(status) in str(error.value) and "private" not in str(error.value)
    assert len(seen) == 1 and stream.closed and stream.yielded == 0


@pytest.mark.parametrize("fault", ["compressed", "oversized", "malformed", "deep"])
async def test_native_uses_same_streaming_response_guards(monkeypatch, fault):
    monkeypatch.setattr(openai_compatible, "MAX_RESPONSE_BYTES", 1000)
    body = b"x" * 1001 if fault == "oversized" else b"not-json"
    headers = {"Content-Encoding": "gzip"} if fault == "compressed" else {}
    if fault == "deep":
        body = b'{"deep":' + b"[" * 65 + b"]" * 65 + b"}"
    stream = RecordingStream([body] if fault == "deep" else [body, b"must-not-read"])
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=stream, headers=headers))
    ) as client:
        with pytest.raises(LlmGatewayError):
            await OpenAiCompatibleGateway(client=client).complete(BASE, "key", "model", REQUEST)
    assert stream.closed
    if fault == "compressed":
        assert stream.yielded == 0
    if fault == "oversized":
        assert stream.yielded == 1


async def test_native_cancellation_closes_stream_and_processing_counts_towards_deadline(
    monkeypatch,
):
    stream = RecordingStream([json.dumps(response_data()).encode()], delay=10)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=stream))
    ) as client:
        task = asyncio.create_task(
            OpenAiCompatibleGateway(client=client).complete(BASE, "key", "model", REQUEST)
        )
        await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert stream.closed
    elapsed = 0

    def delayed_parse(*args):
        nonlocal elapsed
        result = parse_response(*args)
        elapsed = 2
        return result

    monkeypatch.setattr(openai_compatible, "parse_response", delayed_parse)
    monkeypatch.setattr(openai_compatible.time, "perf_counter", lambda: elapsed)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response_data()))
    ) as client:
        with pytest.raises(LlmGatewayError, match="timed out"):
            await OpenAiCompatibleGateway(client=client, timeout_seconds=1).complete(
                BASE, "key", "model", REQUEST
            )


async def test_native_and_compatible_requests_share_one_two_request_admission_limit():
    started, release = asyncio.Event(), asyncio.Event()
    active = maximum = calls = 0

    async def handler(request):
        nonlocal active, maximum, calls
        active += 1
        calls += 1
        maximum = max(maximum, active)
        if calls == 2:
            started.set()
        try:
            await release.wait()
            body = (
                response_data()
                if request.url.path.endswith("/responses")
                else {"choices": [{"message": {"content": "ok"}}]}
            )
            return httpx.Response(200, json=body)
        finally:
            active -= 1

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = OpenAiCompatibleGateway(client=client)
        tasks = [
            asyncio.create_task(gateway.complete(base, "key", "model", REQUEST))
            for base in (BASE, "http://localhost:11434/v1", BASE)
        ]
        await asyncio.wait_for(started.wait(), 1)
        await asyncio.sleep(0)
        assert calls == 2 and maximum == 2
        release.set()
        outcomes = await asyncio.gather(*tasks)
    assert calls == 3 and maximum == 2 and all(result.content for result in outcomes)
