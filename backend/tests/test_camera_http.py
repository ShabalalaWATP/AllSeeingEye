"""Read-only camera POST queries preserve the outbound HTTP security boundary."""

import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.geo import camera_http
from ase.adapters.geo.camera_http import CameraHttpClient

PUBLIC_URL = "https://93.184.216.34/api/cameras/batch"


class ChunkedBody(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks
        self.consumed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        self.consumed = True
        for chunk in self.chunks:
            yield chunk


async def test_post_pins_checked_ip_preserves_tls_name_and_has_no_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = AsyncMock(return_value="93.184.216.34")
    monkeypatch.setattr(camera_http, "assert_public_host", resolver)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == PUBLIC_URL
        assert request.headers["host"] == "opencctv.org"
        assert request.extensions["sni_hostname"] == "opencctv.org"
        assert request.headers["accept-encoding"] == "identity"
        assert request.headers["content-type"] == "application/json"
        assert request.headers["user-agent"] == "ASE-camera-tests/1.0"
        assert "authorization" not in request.headers
        assert "cookie" not in request.headers
        assert json.loads(request.content) == {"ids": ["camera-1"]}
        return httpx.Response(200, json=[{"id": "camera-1"}])

    client = CameraHttpClient(
        "ASE-camera-tests/1.0", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    try:
        assert await client.post_json(
            "https://opencctv.org/api/cameras/batch", {"ids": ["camera-1"]}
        ) == [{"id": "camera-1"}]
        resolver.assert_awaited_once_with("https://opencctv.org/api/cameras/batch")
    finally:
        await client.aclose()


@pytest.mark.parametrize("status", [301, 302, 307, 308, 400, 429, 500])
async def test_post_refuses_redirects_and_errors_without_following(status: int) -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(status, headers={"Location": "http://127.0.0.1/admin"})

    client = CameraHttpClient(
        "test",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True),
    )
    try:
        with pytest.raises(FeedFetchError, match="Camera query refused"):
            await client.post_json(PUBLIC_URL, {"ids": []})
        assert requests == [PUBLIC_URL]
    finally:
        await client.aclose()


async def test_oversized_request_is_rejected_before_dns_or_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver = AsyncMock()
    monkeypatch.setattr(camera_http, "assert_public_host", resolver)
    handler = AsyncMock()
    client = CameraHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    try:
        with pytest.raises(FeedFetchError, match="request limit"):
            await client.post_json(PUBLIC_URL, {"x": "a" * 65536})
        resolver.assert_not_awaited()
        handler.assert_not_awaited()
    finally:
        await client.aclose()


async def test_request_at_64k_limit_is_accepted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert len(request.content) == 65536
        return httpx.Response(200, json={"ok": True})

    client = CameraHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    try:
        assert await client.post_json(PUBLIC_URL, {"x": "a" * 65527}) == {"ok": True}
    finally:
        await client.aclose()


@pytest.mark.parametrize("declared", [False, True])
async def test_oversized_response_is_bounded_with_or_without_content_length(declared: bool) -> None:
    body = ChunkedBody([b"[0,", b"0,0,0]"])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Length": "9"} if declared else {}, stream=body)

    client = CameraHttpClient(
        "test", max_bytes=8, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    try:
        with pytest.raises(FeedFetchError, match=r"too large|exceeded"):
            await client.post_json(PUBLIC_URL, {})
        assert body.consumed is not declared
    finally:
        await client.aclose()


async def test_encoded_response_is_refused_before_decompression() -> None:
    body = ChunkedBody([b"not consumed"])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"Content-Encoding": "gzip"}, stream=body)

    client = CameraHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    try:
        with pytest.raises(FeedFetchError, match="content encoding"):
            await client.post_json(PUBLIC_URL, {})
        assert not body.consumed
    finally:
        await client.aclose()


@pytest.mark.parametrize("kind", ["malformed", "parser-depth-failure"])
async def test_malformed_or_deep_json_is_a_safe_feed_failure(
    kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"not JSON"
    if kind == "parser-depth-failure":
        # CPython versions differ in JSON depth limits; exercise the parser's
        # explicit depth failure deterministically without changing global limits.
        monkeypatch.setattr(camera_http.json, "loads", Mock(side_effect=RecursionError("too deep")))
        payload = b"[" * 2000 + b"0" + b"]" * 2000
    client = CameraHttpClient(
        "test",
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, content=payload))
        ),
    )
    try:
        with pytest.raises(FeedFetchError, match=r"^Camera query failed$"):
            await client.post_json(PUBLIC_URL, {})
    finally:
        await client.aclose()


async def test_transport_failure_does_not_expose_upstream_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("upstream internal diagnostic", request=request)

    client = CameraHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    try:
        with pytest.raises(FeedFetchError, match=r"^Camera query failed$"):
            await client.post_json(PUBLIC_URL, {})
    finally:
        await client.aclose()


@pytest.mark.parametrize("url", ["https://127.0.0.1/batch", "https://user:pw@example.com/batch"])
async def test_private_addresses_and_url_credentials_are_rejected_before_network(url: str) -> None:
    handler = AsyncMock()
    client = CameraHttpClient(
        "test", client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    try:
        with pytest.raises(FeedFetchError):
            await client.post_json(url, {})
        handler.assert_not_awaited()
    finally:
        await client.aclose()


@pytest.mark.parametrize("kind", ["auth", "header"])
async def test_shared_authorisation_cannot_be_attached_to_camera_client(kind: str) -> None:
    kwargs = (
        {"auth": httpx.BasicAuth("test-user", "test-password")}
        if kind == "auth"
        else {"headers": {"Authorization": "Bearer test-placeholder"}}
    )
    async with httpx.AsyncClient(**kwargs) as transport:
        with pytest.raises(ValueError, match="global authorisation"):
            CameraHttpClient("test", client=transport)
