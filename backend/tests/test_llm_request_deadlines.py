"""Long Max report drafts retain bounded transport, processing and cancellation."""

import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from ase.adapters.llm import openai_compatible
from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway
from ase.application.ports.llm import LlmGatewayError
from ase.domain.report_schema import REPORT_BODY_SCHEMA
from test_llm_gateway_security import RecordingStream
from test_openai_responses import BASE, REQUEST, response_data

REPORT_REQUEST = replace(REQUEST, schema_name="report", json_schema=REPORT_BODY_SCHEMA)


@pytest.mark.parametrize(
    "base,effort,schema,override,elapsed,deadline",
    [
        (BASE, "max", "report", None, 150, 300),
        (BASE + "/", "max", "report", None, 150, 300),
        (BASE, "max", "report", None, 301, 300),
        (BASE, "max", "report_topic", None, 150, 300),
        (BASE + "/", "max", "report_topic", None, 301, 300),
        (BASE, "max", "report_synthesis", None, 150, 300),
        (BASE, "max", "report_synthesis", None, 301, 300),
        (BASE, "max", "report_judgements", None, 150, 300),
        (BASE, "max", "report_judgements", None, 301, 300),
        (BASE, "max", "report_context", None, 150, 300),
        (BASE, "max", "report_context", None, 301, 300),
        (BASE, "max", "report_alternatives", None, 150, 300),
        (BASE, "max", "report_collection", None, 150, 300),
        (BASE, "max", "report_alternatives", None, 301, 300),
        (BASE, "max", "report_collection", None, 301, 300),
        (BASE, "max", "report_alternatives", 1, 2, 1),
        (BASE, "max", "report_collection", 1, 2, 1),
        (BASE, "max", "report_judgements", 1, 2, 1),
        (BASE, "max", "report_context", 1, 2, 1),
        (BASE, "max", "report_topic", 1, 2, 1),
        (BASE, "max", "report_synthesis", 1, 2, 1),
        (BASE, "xhigh", "report_topic", None, 121, 120),
        ("http://localhost:11434/v1", "max", "report_synthesis", None, 121, 120),
        (BASE, "max", "report_other", None, 121, 120),
        (BASE, "max", "connection_test", None, 121, 120),
        (BASE, "max", "photo_geolocation", None, 121, 120),
        (BASE, "xhigh", "report", None, 121, 120),
        ("http://localhost:11434/v1", "max", "report", None, 121, 120),
        ("https://api.openai.com:443/v1", "max", "report", None, 121, 120),
        (BASE, "max", "report", 120, 121, 120),
        (BASE, "max", "report", 1, 2, 1),
        (BASE, "max", "report", 600, 400, 600),
    ],
)
async def test_selected_deadline_covers_http_queue_and_response_processing(
    monkeypatch, base, effort, schema, override, elapsed, deadline
):
    clock = 0
    deadlines = []
    calls = []
    original_timeout = asyncio.timeout
    native_parser = openai_compatible.parse_response
    chat_parser = openai_compatible.parse_completion

    def record_timeout(seconds):
        deadlines.append(seconds)
        return original_timeout(seconds)

    def delayed_parse(parser):
        def parse(*args):
            nonlocal clock
            result = parser(*args)
            clock = elapsed
            return result

        return parse

    def handler(request):
        calls.append(request)
        assert set(request.extensions["timeout"].values()) == {deadline}
        body = json.loads(request.content)
        assert body["model"] == "gpt-5.6-luna"
        if request.url.path.endswith("/responses"):
            assert body["reasoning"] == {"effort": effort}
            assert body["store"] is False
            return httpx.Response(200, json=response_data())
        assert body["reasoning_effort"] == effort
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(openai_compatible.asyncio, "timeout", record_timeout)
    monkeypatch.setattr(openai_compatible.time, "perf_counter", lambda: clock)
    monkeypatch.setattr(openai_compatible, "parse_response", delayed_parse(native_parser))
    monkeypatch.setattr(openai_compatible, "parse_completion", delayed_parse(chat_parser))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=2) as client:
        options = {} if override is None else {"timeout_seconds": override}
        gateway = OpenAiCompatibleGateway(client=client, **options)
        request = replace(REPORT_REQUEST, reasoning_effort=effort, schema_name=schema)
        if elapsed > deadline:
            with pytest.raises(LlmGatewayError, match="timed out"):
                await gateway.complete(base, "fixture-key", "gpt-5.6-luna", request)
        else:
            result = await gateway.complete(base, "fixture-key", "gpt-5.6-luna", request)
            assert result.latency_ms == elapsed * 1000
    assert deadlines == [deadline] and len(calls) == 1


@pytest.mark.parametrize("schema", ["report", "report_topic", "report_synthesis"])
async def test_long_native_report_still_obeys_outer_deadline_and_closes_stream(schema):
    stream = RecordingStream([b" "] * 200, delay=0.005)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=stream))
    ) as client:
        gateway = OpenAiCompatibleGateway(client=client)
        with pytest.raises(TimeoutError):
            async with asyncio.timeout(0.04):
                await gateway.complete(
                    BASE, "key", "gpt-5.6-luna", replace(REPORT_REQUEST, schema_name=schema)
                )
    assert stream.closed and stream.yielded < 200


@pytest.mark.parametrize("schema", ["report", "report_topic", "report_synthesis"])
async def test_explicit_native_report_timeout_stops_slow_drip_without_retry(schema):
    stream = RecordingStream([b" "] * 200, delay=0.005)
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, stream=stream)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = OpenAiCompatibleGateway(client=client, timeout_seconds=0.04)
        with pytest.raises(LlmGatewayError, match="timed out"):
            await gateway.complete(
                BASE, "key", "gpt-5.6-luna", replace(REPORT_REQUEST, schema_name=schema)
            )
    assert stream.closed and stream.yielded < 200 and len(calls) == 1
