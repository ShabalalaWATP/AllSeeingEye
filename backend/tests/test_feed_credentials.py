"""Per-request credentials cannot escape exact origins, redirects or shared state."""

import asyncio

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedCredential, FeedFetchError, FeedHttpClient

ORIGIN = "https://service.example"
AUTH = "Basic synthetic-test-header"


@pytest.mark.parametrize(
    "origin",
    [
        "http://service.example",
        "https://service.example/path",
        "https://service.example?key=x",
        "https://service.example#x",
        "https://u:p@service.example",
        "https://@service.example",
        "https://service.example:0",
        "https://[broken",
        "https://service.example:99999",
    ],
)
def test_credential_configuration_requires_an_exact_secure_origin(origin: str) -> None:
    with pytest.raises(ValueError):
        FeedCredential(origin, AUTH)


@pytest.mark.parametrize(
    "value",
    ["", "Basic x\r\nInjected: bad", "x" * 8193, "Basic ü"],
    ids=["empty", "newline", "oversized", "unicode"],
)
def test_invalid_auth_header_values_are_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="authorisation"):
        FeedCredential(ORIGIN, value)


@pytest.mark.parametrize(
    "destination",
    [
        "http://service.example/data",
        "https://service.example.evil/data",
        "https://other.example/data",
        "https://service.example:8443/data",
        "https://@service.example/data",
        "https://[bad",
        "https://service.example/data\n",
    ],
)
async def test_origin_mismatch_is_rejected_before_dns_or_transport(destination: str) -> None:
    client = FeedHttpClient(
        "tests",
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: pytest.fail("No request expected"))
        ),
    )
    with pytest.raises(FeedFetchError, match="origin"):
        await client.get_bytes(destination, credential=FeedCredential(ORIGIN, AUTH))
    await client.aclose()


async def test_concurrent_credentials_are_request_local_and_dns_pinning_preserves_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []
    guarded: list[str] = []

    async def guard(url: str) -> str:
        guarded.append(url)
        return "8.8.8.8"

    async def response(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        await asyncio.sleep(0)
        return httpx.Response(200, json={"ok": True}, headers={"etag": "validator"})

    monkeypatch.setattr(feed_http, "assert_public_host", guard)
    client = FeedHttpClient(
        "tests", client=httpx.AsyncClient(transport=httpx.MockTransport(response))
    )
    first = FeedCredential(ORIGIN, AUTH)
    second = FeedCredential("https://other.example", "Bearer synthetic-other-header")
    await asyncio.gather(
        client.get_json(f"{ORIGIN}/first", credential=first),
        client.get_json("https://other.example/second", credential=second),
        client.get_json("https://public.example/third"),
    )
    assert len(requests) == len(guarded) == 3
    headers = {
        request.headers["host"]: request.headers.get("authorization") for request in requests
    }
    assert headers == {
        "service.example": AUTH,
        "other.example": second.authorization,
        "public.example": None,
    }
    assert all(request.url.host == "8.8.8.8" for request in requests)
    assert requests[0].extensions["sni_hostname"] == "service.example"
    assert "authorization" not in client._client.headers
    assert AUTH not in repr(first)
    assert all("first" not in key and "second" not in key for key in client._validators)
    await client.aclose()


@pytest.mark.parametrize("location", ["https://other.example/secret", "/same-origin"])
async def test_credentials_force_zero_redirects_even_when_caller_requests_more(
    monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    requests = []

    async def guard(url: str) -> None:
        pass

    def response(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(302, headers={"location": location})

    monkeypatch.setattr(feed_http, "assert_public_host", guard)
    client = FeedHttpClient(
        "tests",
        client=httpx.AsyncClient(transport=httpx.MockTransport(response), follow_redirects=True),
    )
    with pytest.raises(FeedFetchError, match="Authenticated") as error:
        await client.get_bytes(
            f"{ORIGIN}/?private=query", credential=FeedCredential(ORIGIN, AUTH), max_redirects=3
        )
    assert len(requests) == 1
    assert "private" not in str(error.value) and AUTH not in str(error.value)
    await client.aclose()


@pytest.mark.parametrize("mode", ["body", "json", "http", "transport", "not-modified"])
async def test_authenticated_errors_never_expose_response_or_request_data(
    monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    async def guard(url: str) -> None:
        pass

    def response(request: httpx.Request) -> httpx.Response:
        if mode == "transport":
            raise httpx.ConnectError(f"secret request: {request.url} {AUTH}")
        status = {"http": 401, "not-modified": 304}.get(mode, 200)
        return httpx.Response(
            status,
            content=b"secret body",
            headers={"content-length": "9999"} if mode == "body" else {},
        )

    monkeypatch.setattr(feed_http, "assert_public_host", guard)
    client = FeedHttpClient(
        "tests", max_bytes=100, client=httpx.AsyncClient(transport=httpx.MockTransport(response))
    )
    with pytest.raises(FeedFetchError) as error:
        await client.get_json(f"{ORIGIN}/?private=query", credential=FeedCredential(ORIGIN, AUTH))
    assert "secret" not in str(error.value) and "private" not in str(error.value)
    await client.aclose()


async def test_authentication_is_not_accepted_on_shared_client() -> None:
    for client in (
        httpx.AsyncClient(headers={"Authorization": AUTH}),
        httpx.AsyncClient(auth=("user", "password")),
    ):
        with pytest.raises(ValueError, match="global authorisation"):
            FeedHttpClient("tests", client=client)
        await client.aclose()


async def test_credentials_ignore_existing_validators_and_do_not_persist_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    async def guard(url: str) -> None:
        pass

    def response(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text="ok", headers={"etag": str(len(requests))})

    monkeypatch.setattr(feed_http, "assert_public_host", guard)
    client = FeedHttpClient(
        "tests", client=httpx.AsyncClient(transport=httpx.MockTransport(response))
    )
    url = f"{ORIGIN}/data"
    await client.get_text(url)
    assert await client.get_text(url, credential=FeedCredential(ORIGIN, AUTH)) == "ok"
    await client.get_text(url)
    assert "if-none-match" not in requests[1].headers
    assert requests[1].headers["authorization"] == AUTH
    assert requests[2].headers["if-none-match"] == "1"
    assert "authorization" not in requests[2].headers
    await client.aclose()
