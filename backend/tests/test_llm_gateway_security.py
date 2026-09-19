"""The completion gateway bounds untrusted replies and never persists provider error bodies."""

from __future__ import annotations

import asyncio
import gzip
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from ase.adapters.llm import openai_compatible
from ase.adapters.llm.openai_compatible import OpenAiCompatibleGateway
from ase.application.ports.feeds import EventQuery
from ase.application.ports.llm import LlmGatewayError
from ase.container import Container
from ase.domain.llm import LlmMessage, LlmRequest
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, USER_EMAIL, USER_PASSWORD, bearer, login_token
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE, filled_store

REQUEST = LlmRequest((LlmMessage("user", "private-prompt-marker"),), 30, 0.0)
SECRET = "test-gateway-secret-marker"
BASE_URL = "http://127.0.0.1:11434/v1"


async def test_direct_gateway_rejects_public_plain_http_before_sending_secret() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: pytest.fail("No HTTP request expected"))
    ) as client:
        with pytest.raises(LlmGatewayError, match="endpoint address is invalid"):
            await OpenAiCompatibleGateway(client=client).complete(
                "http://93.184.216.34/v1", SECRET, "model", REQUEST
            )


class RecordingStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes], delay: float = 0) -> None:
        self.chunks = chunks
        self.delay = delay
        self.yielded = 0
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            if self.delay:
                await asyncio.sleep(self.delay)
            self.yielded += 1
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


async def test_stream_is_closed_as_soon_as_decoded_body_exceeds_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(openai_compatible, "MAX_RESPONSE_BYTES", 128)
    stream = RecordingStream([b" " * 128, b"x", b"must-not-be-read"])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=stream)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LlmGatewayError, match="allowed size"):
            await OpenAiCompatibleGateway(client=client).complete(
                BASE_URL, SECRET, "model", REQUEST
            )
    assert stream.yielded == 2
    assert stream.closed


async def test_compressed_body_is_rejected_before_unbounded_httpx_decoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(openai_compatible, "MAX_RESPONSE_BYTES", 128)
    compressed = gzip.compress(b" " * 256)
    stream = RecordingStream([compressed, b"must-not-be-read"])

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(
            200,
            stream=stream,
            headers={"Content-Encoding": "gzip", "Content-Length": str(len(compressed))},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LlmGatewayError, match="compressed content"):
            await OpenAiCompatibleGateway(client=client).complete(
                BASE_URL, SECRET, "model", REQUEST
            )
    assert stream.yielded == 0 and stream.closed


async def test_total_deadline_stops_a_slow_drip_and_closes_the_stream() -> None:
    stream = RecordingStream([b" "] * 200, delay=0.005)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=stream)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=10) as client:
        gateway = OpenAiCompatibleGateway(client=client, timeout_seconds=0.04)
        with pytest.raises(LlmGatewayError, match="timed out"):
            await asyncio.wait_for(
                gateway.complete(BASE_URL, SECRET, "model", REQUEST), timeout=0.5
            )
    assert stream.yielded < 200 and stream.closed


async def test_admission_caps_concurrency_and_queue_wait_uses_total_deadline() -> None:
    active = maximum = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        try:
            await asyncio.sleep(0.12)
            return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})
        finally:
            active -= 1

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        gateway = OpenAiCompatibleGateway(client=client, timeout_seconds=0.2)
        outcomes = await asyncio.gather(
            *(gateway.complete(BASE_URL, SECRET, "model", REQUEST) for _ in range(3)),
            return_exceptions=True,
        )
    assert maximum == 2 and active == 0
    assert not isinstance(outcomes[0], Exception) and not isinstance(outcomes[1], Exception)
    assert isinstance(outcomes[2], LlmGatewayError)
    assert "timed out" in str(outcomes[2])


@pytest.mark.parametrize("status", [301, 302, 307, 308, 401, 403, 429, 503])
async def test_status_errors_never_read_provider_body_or_follow_redirect(status: int) -> None:
    seen: list[httpx.Request] = []
    stream = RecordingStream([f"{SECRET} private-prompt-marker upstream-only-marker".encode()])

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if len(seen) > 1:
            return httpx.Response(200, json={"choices": [{"message": {"content": "redirected"}}]})
        return httpx.Response(
            status, stream=stream, headers={"Location": "http://other-endpoint.test/"}
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as client:
        with pytest.raises(LlmGatewayError) as caught:
            await OpenAiCompatibleGateway(client=client).complete(
                BASE_URL, SECRET, "model", REQUEST
            )
    assert str(status) in str(caught.value)
    assert all(
        text not in str(caught.value)
        for text in (SECRET, "private-prompt-marker", "upstream-only-marker")
    )
    assert len(seen) == 1 and stream.yielded == 0 and stream.closed


@pytest.mark.parametrize(
    "body",
    [b"[" * 2000, b'{"x":' + b"[" * 2000 + b"]" * 2000 + b"}", b"invalid \xff"],
    ids=["truncated-nesting", "valid-excessive-depth", "invalid-unicode"],
)
async def test_malformed_and_deep_json_return_safe_gateway_errors(body: bytes) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LlmGatewayError, match="invalid JSON"):
            await OpenAiCompatibleGateway(client=client).complete(
                BASE_URL, SECRET, "model", REQUEST
            )


@pytest.mark.parametrize("error_type", [httpx.ReadTimeout, httpx.ConnectError, httpx.DecodingError])
async def test_transport_errors_do_not_include_transport_detail(
    error_type: type[httpx.HTTPError],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise error_type(f"{SECRET} {BASE_URL} private-prompt-marker")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LlmGatewayError) as caught:
            await OpenAiCompatibleGateway(client=client).complete(
                BASE_URL, SECRET, "model", REQUEST
            )
    assert SECRET not in str(caught.value)
    assert BASE_URL not in str(caught.value)
    assert "private-prompt-marker" not in str(caught.value)


async def test_provider_error_is_safe_in_persisted_reports_and_usage(
    client: httpx.AsyncClient, container: Container, admin: User, user: User
) -> None:
    admin_token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    user_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    profile = {**PROFILE, "api_key": SECRET}
    await seed_legacy_profile(container, profile)
    # With no evidence the pipeline writes a coverage-gap report without calling the model,
    # so seed evidence to exercise the model failure this test guards.
    container.store.upsert(list(filled_store().query(EventQuery(limit=10))))

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == f"Bearer {SECRET}"
        return httpx.Response(
            401, json={"error": {"message": f"key={SECRET} upstream-only-marker"}}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as upstream:
        container.llm = OpenAiCompatibleGateway(client=upstream)
        response = await client.post(
            "/api/reports", json={"template": "intsum"}, headers=bearer(user_token)
        )
    assert response.status_code == 201
    assert response.json()["report"]["status"] == "failed"
    report_id = response.json()["report"]["id"]
    stored = await client.get(f"/api/reports/{report_id}", headers=bearer(user_token))
    usage = await client.get("/api/admin/llm/usage", headers=bearer(admin_token))
    assert stored.status_code == usage.status_code == 200
    for result in (response, stored, usage):
        assert SECRET not in result.text and "upstream-only-marker" not in result.text
        assert "401" in result.text


async def test_successful_local_response_still_preserves_schema_and_usage() -> None:
    payload = {
        "choices": [{"message": {"content": "answer"}}],
        "usage": {"prompt_tokens": 2, "completion_tokens": 1},
    }
    body = json.dumps(payload).encode()
    stream = RecordingStream([body[:20], body[20:]])

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "127.0.0.1"
        assert json.loads(request.content)["messages"][0]["content"] == "private-prompt-marker"
        return httpx.Response(200, stream=stream)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAiCompatibleGateway(client=client).complete(
            BASE_URL, SECRET, "local", REQUEST
        )
    assert result.content == "answer" and result.model == "local"
    assert result.prompt_tokens == 2 and result.completion_tokens == 1
    assert stream.closed


@pytest.mark.parametrize("value", [True, -1, 2_147_483_648, "3"])
def test_compatible_usage_rejects_invalid_provider_counters(value: object) -> None:
    result = openai_compatible.parse_completion(
        {
            "choices": [{"message": {"content": "answer"}}],
            "usage": {"prompt_tokens": value, "completion_tokens": value},
        },
        "model",
        1,
    )
    assert result.prompt_tokens is None and result.completion_tokens is None


@pytest.mark.parametrize("parser_name", ["_bounded_json", "parse_completion"])
async def test_all_response_processing_counts_towards_deadline(
    monkeypatch: pytest.MonkeyPatch, parser_name: str
) -> None:
    elapsed = 0.0
    original = getattr(openai_compatible, parser_name)

    def timed_parse(*args: Any) -> Any:
        nonlocal elapsed
        result = original(*args)
        elapsed = 2.0
        return result

    monkeypatch.setattr(openai_compatible, parser_name, timed_parse)
    monkeypatch.setattr(openai_compatible.time, "perf_counter", lambda: elapsed)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(LlmGatewayError, match="timed out"):
            await OpenAiCompatibleGateway(client=client, timeout_seconds=1).complete(
                BASE_URL, SECRET, "model", REQUEST
            )
