"""Offline pinned-HTTPS and byte-boundary tests for selected originals."""

import asyncio
from dataclasses import replace

import httpx
import pytest

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.research import original_http
from ase.adapters.research.original_http import GuardedOriginalHttp
from ase.application.research.original_policy import (
    OriginalFetchRejected,
    OriginalFetchRequest,
    validate_response,
)
from original_acquisition_support import ADDRESS, NOW, URL, Harness, policy


class Clock:
    def now(self):
        return NOW


def request(**changes):
    reviewed = policy(max_bytes=16)
    values = {
        "url": URL,
        "policy": reviewed,
        "max_bytes": reviewed.max_bytes,
        "max_redirects": reviewed.max_redirects,
        "timeout_seconds": reviewed.timeout_seconds,
    }
    return OriginalFetchRequest(**(values | changes))


def adapter(monkeypatch, handler, *, guard=None, admit=None):
    async def public(_url):
        return ADDRESS

    async def allowed(_source_id, _url):
        return True

    monkeypatch.setattr(original_http, "assert_public_host", guard or public)
    return GuardedOriginalHttp(
        "ASE-original-tests/1.0",
        Clock(),
        admit or allowed,
        transport=httpx.MockTransport(handler),
    )


async def test_pinned_hops_preserve_original_host_and_sni_without_cookies(monkeypatch):
    seen, admitted = [], []

    def respond(sent):
        seen.append(sent)
        assert str(sent.url).startswith(f"https://{ADDRESS}/")
        assert sent.headers["host"] == "publisher.example"
        assert sent.headers["accept-encoding"] == "identity"
        assert sent.extensions["sni_hostname"] == "publisher.example"
        assert "cookie" not in sent.headers and "authorization" not in sent.headers
        if sent.url.path == "/report.txt":
            return httpx.Response(
                302,
                headers={"location": "/corrected.txt", "set-cookie": "sid=untrusted"},
            )
        return httpx.Response(
            200,
            stream=httpx.ByteStream(b"Original text"),
            headers={
                "content-type": "text/plain; charset=utf-8",
                "last-modified": "Mon, 14 Sep 2026 09:00:00 GMT",
                "etag": '"revision-2"',
            },
        )

    async def admit(source_id, url):
        admitted.append((source_id, url))
        return True

    fetcher = adapter(monkeypatch, respond, admit=admit)
    incoming = request(max_bytes=16)
    result = await fetcher.fetch(incoming)
    assert len(seen) == len(result.hops) == len(admitted) == 2
    assert result.requested_url == URL
    assert result.canonical_url == "https://publisher.example/corrected.txt"
    assert result.body == b"Original text"
    assert result.wire_body_bytes == len(result.body)
    assert result.last_modified_at.isoformat() == "2026-09-14T09:00:00+00:00"
    assert result.etag == '"revision-2"'
    assert validate_response(result, incoming, incoming.policy, NOW) is None


@pytest.mark.parametrize(
    ("response", "reason"),
    [
        (
            httpx.Response(
                200,
                stream=httpx.ByteStream(b"x" * 17),
                headers={"content-type": "text/plain"},
            ),
            "body_limit_or_size_mismatch",
        ),
        (
            httpx.Response(
                200, content=b"x", headers={"content-type": "text/plain", "content-length": "17"}
            ),
            "body_limit_or_size_mismatch",
        ),
        (
            httpx.Response(
                200,
                stream=httpx.ByteStream(b"x"),
                headers={"content-type": "text/plain", "content-length": "2"},
            ),
            "body_limit_or_size_mismatch",
        ),
        (
            httpx.Response(
                200,
                content=b"x",
                headers={"content-type": "text/plain", "content-encoding": "gzip"},
            ),
            "compressed_response_not_permitted",
        ),
        (
            httpx.Response(200, content=b"<b>x</b>", headers={"content-type": "text/html"}),
            "unsupported_media_type",
        ),
        (
            httpx.Response(206, content=b"x", headers={"content-type": "text/plain"}),
            "http_status_not_permitted",
        ),
    ],
)
async def test_oversize_compressed_html_and_partial_responses_fail(monkeypatch, response, reason):
    fetcher = adapter(monkeypatch, lambda _: response)
    with pytest.raises(OriginalFetchRejected, match=reason):
        await fetcher.fetch(request())


async def test_exact_byte_ceiling_is_accepted(monkeypatch):
    fetcher = adapter(
        monkeypatch,
        lambda _: httpx.Response(
            200,
            stream=httpx.ByteStream(b"x" * 16),
            headers={"content-type": "text/plain"},
        ),
    )
    assert len((await fetcher.fetch(request())).body) == 16


async def test_direct_private_url_is_denied_before_dns_or_http(monkeypatch):
    async def no_dns(_url):
        pytest.fail("No DNS request expected")

    fetcher = adapter(
        monkeypatch,
        lambda _: pytest.fail("No HTTP request expected"),
        guard=no_dns,
    )
    with pytest.raises(OriginalFetchRejected, match="request_not_permitted"):
        await fetcher.fetch(request(url="https://127.0.0.1/admin"))


async def test_redirect_to_private_host_is_denied_before_second_dispatch(monkeypatch):
    sent = []

    def respond(_request):
        sent.append(1)
        return httpx.Response(302, headers={"location": "https://127.0.0.1/admin"})

    fetcher = adapter(monkeypatch, respond)
    with pytest.raises(OriginalFetchRejected, match="destination_not_permitted"):
        await fetcher.fetch(request())
    assert len(sent) == 1


async def test_redirect_dns_rebinding_is_denied_after_first_public_hop(monkeypatch):
    resolved, sent = [], []

    async def guard(url):
        resolved.append(url)
        if url.endswith("/redirected.txt"):
            raise FeedFetchError("Refusing private DNS answer")
        return ADDRESS

    def respond(_request):
        sent.append(1)
        return httpx.Response(302, headers={"location": "/redirected.txt"})

    fetcher = adapter(monkeypatch, respond, guard=guard)
    with pytest.raises(OriginalFetchRejected, match="destination_not_permitted"):
        await fetcher.fetch(request())
    assert len(resolved) == 2 and len(sent) == 1


async def test_source_hop_admission_stops_before_dns_and_network(monkeypatch):
    async def deny(_source_id, _url):
        return False

    async def no_dns(_url):
        pytest.fail("No DNS request expected")

    fetcher = adapter(
        monkeypatch,
        lambda _: pytest.fail("No HTTP request expected"),
        guard=no_dns,
        admit=deny,
    )
    with pytest.raises(OriginalFetchRejected, match="source_rate_or_terms_not_permitted"):
        await fetcher.fetch(request())


async def test_admission_failure_and_transport_error_have_safe_codes(monkeypatch):
    async def unavailable(_source_id, _url):
        raise RuntimeError("private rate-service detail")

    blocked = adapter(
        monkeypatch,
        lambda _: pytest.fail("No HTTP request expected"),
        admit=unavailable,
    )
    with pytest.raises(OriginalFetchRejected, match="source_admission_failed"):
        await blocked.fetch(request())

    def disconnected(_request):
        raise httpx.ConnectError("private transport detail")

    failed = adapter(monkeypatch, disconnected)
    with pytest.raises(OriginalFetchRejected, match="transport_failed"):
        await failed.fetch(request())


async def test_empty_response_and_invalid_user_agent_fail_closed(monkeypatch):
    fetcher = adapter(
        monkeypatch,
        lambda _: httpx.Response(
            200,
            stream=httpx.ByteStream(b""),
            headers={"content-type": "text/plain"},
        ),
    )
    with pytest.raises(OriginalFetchRejected, match="body_limit_or_size_mismatch"):
        await fetcher.fetch(request())

    async def allowed(_source_id, _url):
        return True

    with pytest.raises(ValueError, match="user agent"):
        GuardedOriginalHttp("bad\nagent", Clock(), allowed)


async def test_public_ip_destination_uses_literal_checked_address(monkeypatch):
    async def literal(_url):
        return None

    seen = []

    def respond(sent):
        seen.append(sent)
        return httpx.Response(
            200,
            stream=httpx.ByteStream(b"Public source"),
            headers={"content-type": "text/plain"},
        )

    fetcher = adapter(monkeypatch, respond, guard=literal)
    url = f"https://{ADDRESS}/report.txt"
    incoming = request(
        url=url, policy=policy(max_bytes=16, allowed_origins=(f"https://{ADDRESS}",))
    )
    result = await fetcher.fetch(incoming)
    assert result.canonical_url == url
    assert len(seen) == 1 and "sni_hostname" not in seen[0].extensions


async def test_redirect_limit_and_per_hop_deadline_are_bounded(monkeypatch):
    fetcher = adapter(
        monkeypatch,
        lambda _: httpx.Response(302, headers={"location": "/again.txt"}),
    )
    with pytest.raises(OriginalFetchRejected, match="redirect_limit"):
        await fetcher.fetch(request(max_redirects=0))

    async def wait_forever(_request):
        await asyncio.Event().wait()

    timed = adapter(monkeypatch, wait_forever)
    with pytest.raises(OriginalFetchRejected, match="fetch_timeout"):
        await timed.fetch(request(timeout_seconds=0.02))


async def test_safe_failure_reason_is_retained_as_headline_only():
    harness = Harness()

    async def rejected(_request):
        raise OriginalFetchRejected("compressed_response_not_permitted")

    harness.service.fetch = rejected
    result = await harness.acquire()
    assert result.receipt.status == "headline_only"
    assert result.receipt.reason == "compressed_response_not_permitted"
    assert result.document is None and result.original_bytes == b""
    assert result.receipt.transport_requests is None


async def test_unreviewed_or_expanded_request_cannot_construct_transport_permission(monkeypatch):
    fetcher = adapter(
        monkeypatch,
        lambda _: pytest.fail("No HTTP request expected"),
    )
    invalid = replace(request(), max_bytes=17)

    with pytest.raises(OriginalFetchRejected, match="request_not_permitted"):
        await fetcher.fetch(invalid)
