"""Native web search confirms actual calls, bounds responses, and never echoes credentials."""

import asyncio
import json
from dataclasses import replace

import httpx
import pytest

from ase.adapters.llm import openai_web_search
from ase.adapters.llm.openai_web_search import OpenAiWebSearchGateway, web_payload
from ase.adapters.llm.web_search_response import parse_web_response
from ase.application.ports.web_search import WebSearchError, WebSearchRequest
from test_llm_gateway_security import RecordingStream
from web_search_helpers import CITATION, RESULT, TEXT, URL, native_response

REQUEST = WebSearchRequest('{"question":"public-scope"}', 8000, "max")


def test_search_instructions_preserve_claimants_and_distinguish_event_dates_from_page_dates():
    instructions = web_payload("configured-model", REQUEST)["instructions"]
    assert "Preserve the actual claimant for every reported assertion" in instructions
    assert "a publisher relaying a claim is not the claimant" in instructions
    assert "Do not change which party made the claim" in instructions
    assert "Check the original event date" in instructions
    assert "republication, page updates and search indexes do not establish the event date" in (
        instructions
    )
    assert "Treat reused historical claims as background" in instructions
    assert "unresolved event dates as uncertain, never as current-period facts" in instructions


@pytest.mark.parametrize("budget", [1, 6000, 8000, 16000])
async def test_fixed_origin_native_search_requires_live_tool_and_keeps_configured_model(budget):
    calls = []

    def handler(request):
        calls.append(request)
        assert str(request.url) == "https://api.openai.com/v1/responses"
        assert request.headers["authorization"] == "Bearer fixture-key"
        payload = json.loads(request.content)
        assert payload["model"] == "configured-model"
        assert payload["reasoning"] == {"effort": "max"}
        assert payload["tool_choice"] == "auto"
        assert "must execute the live web-search tool before answering" in payload["instructions"]
        assert "all selected countries within at most two tool calls" in payload["instructions"]
        assert "then stop calling tools and give the final answer" in payload["instructions"]
        assert "report coverage gaps without further searches" in payload["instructions"]
        assert payload["tools"] == [{"type": "web_search", "external_web_access": True}]
        assert payload["max_tool_calls"] == 3 and payload["max_output_tokens"] == budget
        assert payload["store"] is False and "fixture-key" not in request.content.decode()
        return httpx.Response(200, json=native_response())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAiWebSearchGateway(client=client).search(
            "fixture-key", "configured-model", replace(REQUEST, max_output_tokens=budget)
        )
    assert len(calls) == 1
    assert result.synthesis == TEXT and result.citations == (CITATION,)
    assert result.consulted_urls == (URL,) and result.tool_calls == 1
    assert result.prompt_tokens == 30 and result.completion_tokens == 15


@pytest.mark.parametrize(
    "change",
    [
        "no_search",
        "failed_tool",
        "unfinished_after_search",
        "fourth_searching",
        "too_many",
        "incomplete",
        "uncited",
        "only_open_page",
        "unsafe_url",
    ],
)
def test_generated_text_is_not_accepted_without_complete_native_search_and_safe_citations(change):
    data = native_response()
    if change == "no_search":
        data["output"].pop(0)
    elif change == "failed_tool":
        data["output"][0]["status"] = "failed"
    elif change in {"unfinished_after_search", "fourth_searching"}:
        completed = data["output"][0]
        data["output"] = [completed] * (3 if change == "fourth_searching" else 1) + [
            {**completed, "status": "searching"},
            data["output"][1],
        ]
    elif change == "only_open_page":
        data["output"][0]["action"]["type"] = "open_page"
    elif change == "too_many":
        data["output"] = [data["output"][0]] * 4 + [data["output"][1]]
    elif change == "incomplete":
        data["status"] = "incomplete"
    elif change == "uncited":
        data["output"][1]["content"][0]["annotations"] = []
    else:
        data["output"][1]["content"][0]["annotations"][0]["url"] = "http://127.0.0.1/admin"
    result = parse_web_response(data, "fallback", 3)
    assert result.failure and not result.synthesis and not result.citations
    assert result.prompt_tokens == 30 and result.completion_tokens == 15


def test_text_citations_are_bounded_and_multi_part_offsets_are_adjusted():
    data = native_response()
    data["output"][1]["content"].append(
        {
            "type": "output_text",
            "text": "Other finding.",
            "annotations": [
                {
                    "type": "url_citation",
                    "url": URL + "/other",
                    "title": "Other",
                    "start_index": 0,
                    "end_index": 14,
                }
            ],
        }
    )
    result = parse_web_response(data, "fallback", 0)
    assert result.citations[1].start_index == len(TEXT) + 2
    assert result.citations[1].end_index == len(TEXT) + 16
    assert result.synthesis.endswith("\n\nOther finding.")
    data["output"][1]["content"][0]["text"] = "a" * 8000
    result = parse_web_response(data, "fallback", 0)
    assert len(result.synthesis) == 6000 and len(result.citations) == 1


@pytest.mark.parametrize("data", [None, [], {}, {"output": None}, {"output": [{}]}])
def test_malformed_payloads_fail_safely(data):
    result = parse_web_response(data, "fallback", 0)
    assert result.failure and result.synthesis == ""


@pytest.mark.parametrize(
    "malformed",
    ["content_null", "annotations_null", "text_object", "annotation_string", "indices_string"],
)
def test_malformed_nested_response_fields_are_never_promoted_to_context(malformed):
    data = native_response()
    message = data["output"][1]
    if malformed == "content_null":
        message["content"] = None
    elif malformed == "annotations_null":
        message["content"][0]["annotations"] = None
    elif malformed == "text_object":
        message["content"][0]["text"] = {"unknown": "shape"}
    elif malformed == "annotation_string":
        message["content"][0]["annotations"] = ["not-a-citation"]
    else:
        message["content"][0]["annotations"][0]["end_index"] = "43"
    result = parse_web_response(data, "fallback", 0)
    assert result.failure and not result.synthesis and not result.citations
    assert result.prompt_tokens == 30


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(401, text="secret-upstream-body"),
        httpx.Response(
            302, headers={"location": "https://other.example"}, text="secret-upstream-body"
        ),
        httpx.Response(200, text="not-json-secret-upstream-body"),
        httpx.Response(200, headers={"content-encoding": "gzip"}, content=b""),
    ],
)
async def test_provider_error_and_redirect_bodies_never_escape(response):
    calls = []

    def handler(request):
        calls.append(request)
        return response

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(WebSearchError) as error:
            await OpenAiWebSearchGateway(client=client).search("fixture-key", "model", REQUEST)
    assert "secret-upstream-body" not in str(error.value)
    assert "fixture-key" not in str(error.value) and len(calls) == 1


async def test_stream_caps_stop_reading_and_cancellation_closes_network(monkeypatch):
    monkeypatch.setattr(openai_web_search, "MAX_RESPONSE_BYTES", 50)
    stream = RecordingStream([b" " * 50, b"x", b"must-not-read"])
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=stream))
    ) as client:
        with pytest.raises(WebSearchError, match="byte limit"):
            await OpenAiWebSearchGateway(client=client).search("key", "model", REQUEST)
    assert stream.closed and stream.yielded == 2
    slow = RecordingStream([b"{}"], delay=10)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, stream=slow))
    ) as client:
        task = asyncio.create_task(
            OpenAiWebSearchGateway(client=client).search("key", "model", REQUEST)
        )
        await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert slow.closed


async def test_deadline_and_network_failure_are_safe():
    async def slow(_):
        await asyncio.sleep(1)
        return httpx.Response(200, json=native_response())

    async with httpx.AsyncClient(transport=httpx.MockTransport(slow)) as client:
        with pytest.raises(WebSearchError, match="deadline"):
            await OpenAiWebSearchGateway(client=client, timeout_seconds=0.005).search(
                "key", "model", REQUEST
            )

    def failed(_):
        raise httpx.ConnectError("secret-upstream-body")

    async with httpx.AsyncClient(transport=httpx.MockTransport(failed)) as client:
        with pytest.raises(WebSearchError, match="Could not reach") as error:
            await OpenAiWebSearchGateway(client=client).search("key", "model", REQUEST)
    assert "secret-upstream-body" not in str(error.value)


async def test_key_and_request_bounds_before_network():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail())) as client:
        gateway = OpenAiWebSearchGateway(client=client)
        with pytest.raises(WebSearchError, match="API key"):
            await gateway.search("", "model", REQUEST)
        with pytest.raises(WebSearchError, match="bounds"):
            await gateway.search("key", "model", WebSearchRequest("x" * 12001, 10, None))


@pytest.mark.parametrize("budget", [0, -1, 16001, 32000, True, 6000.5, "6000", None])
async def test_invalid_token_budgets_fail_before_network(budget):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail())) as client:
        with pytest.raises(WebSearchError, match="output-token budget"):
            await OpenAiWebSearchGateway(client=client).search(
                "fixture-key", "model", replace(REQUEST, max_output_tokens=budget)
            )


@pytest.mark.parametrize("calls", [1, 2, 3])
def test_normal_native_response_keeps_unknown_publication_date_unknown(calls):
    data = native_response()
    data["output"] = [data["output"][0]] * calls + [data["output"][1]]
    result = parse_web_response(data, "fallback", 25)
    assert result == replace(RESULT, tool_calls=calls) and not hasattr(result, "published_at")
