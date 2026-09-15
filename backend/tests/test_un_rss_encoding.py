"""Unauthenticated feeds that ignore Accept-Encoding: identity decode bounded raw gzip."""

import gzip
from collections.abc import AsyncIterator

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedCredential, FeedFetchError, FeedHttpClient
from ase.adapters.feeds.rss import RssConnector
from ase.adapters.feeds.rss_seeds_official import OFFICIAL_SEEDS
from ase.adapters.feeds.rss_seeds_uk_news import UK_NEWS_SEEDS

URLS = (
    "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
    "https://press.un.org/en/rss.xml",
)
USER_AGENT = "TheAllSeeingEye/0.1 (+operator@example.test)"


class Chunks(httpx.AsyncByteStream):
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.consumed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        self.consumed = True
        for offset in range(0, len(self.content), 7):
            yield self.content[offset : offset + 7]


@pytest.fixture(autouse=True)
def resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    async def public(url: str) -> str:
        return "8.8.8.8"

    monkeypatch.setattr(feed_http, "assert_public_host", public)


async def fetch(
    body: Chunks,
    *,
    url: str = URLS[0],
    limit: int = 1000,
    encoding: str = "gzip",
    declared: str | None = None,
    credential: FeedCredential | None = None,
) -> bytes:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.headers["accept-encoding"] == "identity"
        assert request.headers["user-agent"] == USER_AGENT
        assert "digitraffic-user" not in request.headers
        assert request.url.host == "8.8.8.8"
        headers = {"content-encoding": encoding}
        if declared is not None:
            headers["content-length"] = declared
        return httpx.Response(200, headers=headers, stream=body)

    client = FeedHttpClient(
        USER_AGENT,
        max_bytes=limit,
        client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
    )
    try:
        return await client.get_bytes(url, conditional=False, credential=credential)
    finally:
        await client.aclose()


@pytest.mark.parametrize("url", URLS)
async def test_verified_un_endpoints_decode_chunked_gzip(url: str) -> None:
    assert await fetch(Chunks(gzip.compress(b"<rss/>")), url=url) == b"<rss/>"


async def test_gzip_exact_limit_and_empty_stream() -> None:
    assert await fetch(Chunks(gzip.compress(b"x" * 200)), limit=200) == b"x" * 200
    assert await fetch(Chunks(gzip.compress(b""))) == b""


@pytest.mark.parametrize(
    "url",
    (URLS[0] + "?extra=1", "https://www.independent.co.uk/news/uk/rss", "https://other.test/rss"),
)
async def test_any_unauthenticated_feed_decodes_gzip_it_did_not_ask_for(url: str) -> None:
    assert await fetch(Chunks(gzip.compress(b"<rss/>")), url=url) == b"<rss/>"


@pytest.mark.parametrize("encoding", ("br", "deflate", "gzip, identity", "unknown"))
async def test_other_encodings_are_rejected_before_body_consumption(encoding: str) -> None:
    body = Chunks(b"untrusted")
    with pytest.raises(FeedFetchError, match="Unsupported response content encoding: "):
        await fetch(body, encoding=encoding)
    assert not body.consumed


async def test_identity_response_keeps_existing_path() -> None:
    assert await fetch(Chunks(b"plain"), encoding="identity") == b"plain"


@pytest.mark.parametrize(
    "content",
    (
        gzip.compress(b"x")[:-2],
        gzip.compress(b"x") + b"trailing",
        gzip.compress(b"x") + gzip.compress(b"y"),
        b"not gzip",
    ),
)
async def test_truncated_invalid_and_concatenated_streams_are_rejected(content: bytes) -> None:
    with pytest.raises(FeedFetchError, match="gzip"):
        await fetch(Chunks(content))


async def test_compressed_and_expanded_caps_are_independent() -> None:
    with pytest.raises(FeedFetchError, match="compressed"):
        await fetch(Chunks(gzip.compress(b"small")), limit=10)
    with pytest.raises(FeedFetchError, match="decoded"):
        await fetch(Chunks(gzip.compress(b"x" * 1_000_000)), limit=200)
    body = Chunks(gzip.compress(b"small"))
    with pytest.raises(FeedFetchError, match="compressed"):
        await fetch(body, limit=100, declared="101")
    assert not body.consumed


async def test_credentialed_request_does_not_gain_gzip_support() -> None:
    body = Chunks(gzip.compress(b"small"))
    credential = FeedCredential("https://news.un.org", "Bearer synthetic-test-value")
    with pytest.raises(FeedFetchError, match="Authenticated feed request failed"):
        await fetch(body, credential=credential)
    assert not body.consumed


async def test_redirected_gzip_is_decoded_after_each_hop_is_rechecked() -> None:
    calls = 0
    checked: list[str] = []

    async def public(url: str) -> str:
        checked.append(url)
        return "8.8.8.8"

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(302, headers={"location": URLS[1]})
        body = Chunks(gzip.compress(b"<rss/>"))
        return httpx.Response(200, headers={"content-encoding": "gzip"}, stream=body)

    client = FeedHttpClient(
        USER_AGENT, client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
    )
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(feed_http, "assert_public_host", public)
            assert await client.get_bytes("https://other.test/feed") == b"<rss/>"
        assert checked == ["https://other.test/feed", URLS[1]]
    finally:
        await client.aclose()


async def test_header_token_in_the_error_is_bounded_and_plain() -> None:
    body = Chunks(b"untrusted")
    with pytest.raises(FeedFetchError) as caught:
        await fetch(body, encoding="<script>" + "z" * 100)
    assert str(caught.value) == "Unsupported response content encoding: " + "script" + "z" * 32


@pytest.mark.parametrize("source_id", ("un_news", "un_press", "news_independent_uk"))
async def test_un_gzip_response_reaches_the_existing_rss_parser(source_id: str, clock) -> None:
    payload = (
        b"<rss><channel><item><guid>example</guid><title>Example headline</title>"
        b"<pubDate>Thu, 10 Sep 2026 10:00:00 GMT</pubDate></item></channel></rss>"
    )

    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-encoding": "gzip"}, stream=Chunks(gzip.compress(payload))
        )

    client = FeedHttpClient(
        USER_AGENT, client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
    )
    seed = next(seed for seed in (*OFFICIAL_SEEDS, *UK_NEWS_SEEDS) if seed.spec.id == source_id)
    try:
        events = await RssConnector(client, clock, seed.spec, seed.options).fetch()
        assert len(events) == 1
        assert events[0].source_id == source_id
        assert events[0].title == "Example headline"
    finally:
        await client.aclose()
