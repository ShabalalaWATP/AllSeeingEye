"""Mandatory gzip is decoded under independent compressed and expanded byte limits."""

import gzip

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.digitraffic_http import DigitrafficHttpClient
from ase.adapters.feeds.http import FeedFetchError


class Chunks(httpx.AsyncByteStream):
    def __init__(self, content):
        self.content = content

    async def __aiter__(self):
        for offset in range(0, len(self.content), 7):
            yield self.content[offset : offset + 7]


@pytest.fixture(autouse=True)
def resolve(monkeypatch):
    async def public(url):
        return "8.8.8.8"

    monkeypatch.setattr(feed_http, "assert_public_host", public)


async def fetch(content, *, limit=1000, encoding="gzip"):
    def respond(request):
        assert request.headers["accept-encoding"] == "gzip"
        assert request.headers["user-agent"] == "TheAllSeeingEye/0.1"
        assert request.headers["digitraffic-user"] == "TheAllSeeingEye/0.1"
        assert request.headers["host"] == "meri.digitraffic.fi"
        assert request.url.host == "8.8.8.8"
        return httpx.Response(200, headers={"content-encoding": encoding}, stream=Chunks(content))

    client = DigitrafficHttpClient(
        "private-contact@example.test",
        max_bytes=limit,
        client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
    )
    try:
        return await client.get_bytes(
            "https://meri.digitraffic.fi/api/ais/v1/locations", conditional=False
        )
    finally:
        await client.aclose()


async def test_chunked_gzip_and_identity():
    assert await fetch(gzip.compress(b'{"features": []}')) == b'{"features": []}'
    assert await fetch(b"plain", encoding="identity") == b"plain"


@pytest.mark.parametrize(
    "content",
    [
        gzip.compress(b"x")[:-2],
        gzip.compress(b"x") + b"trailing",
        gzip.compress(b"x") + gzip.compress(b"y"),
        b"not gzip",
    ],
)
async def test_invalid_or_concatenated_gzip_rejected(content):
    with pytest.raises(FeedFetchError, match="gzip"):
        await fetch(content)


async def test_compressed_and_decoded_caps():
    with pytest.raises(FeedFetchError, match="compressed"):
        await fetch(gzip.compress(b"small"), limit=10)
    with pytest.raises(FeedFetchError, match="decoded"):
        await fetch(gzip.compress(b"x" * 100000), limit=200)
    with pytest.raises(FeedFetchError, match="encoding"):
        await fetch(b"x", encoding="br")
