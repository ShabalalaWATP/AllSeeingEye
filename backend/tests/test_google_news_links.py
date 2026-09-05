"""Lazy legacy decoding rejects unsafe links and preserves opaque modern article URLs."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import replace

import pytest

from ase.adapters.feeds import google_news_links
from ase.adapters.feeds.google_news_links import GoogleNewsUrlResolver, decode_embedded_url
from ase.adapters.feeds.http import FeedFetchError
from ase.application.reports import resolve_links
from ase.application.reports.resolve_links import MAX_RESOLVED_LINKS, resolve_cited_links
from ase.domain.evidence import EvidenceItem
from feeds_helpers import NOW, make_event


def envelope(payload: bytes) -> str:
    return "https://news.google.com/rss/articles/" + base64.urlsafe_b64encode(
        payload
    ).decode().rstrip("=")


def embedded(target: str) -> str:
    raw = target.encode()
    size = len(raw)
    length = bytearray()
    while size >= 128:
        length.append((size & 127) | 128)
        size >>= 7
    length.append(size)
    return envelope(b'\x08\x13"' + length + raw + b"\xd2\x01\x00")


@pytest.mark.parametrize(
    "target", ["https://example.com/story", "https://example.com/" + "a" * 150]
)
def test_decodes_short_and_multibyte_length_delimited_urls(target: str) -> None:
    assert decode_embedded_url(embedded(target) + "?oc=5") == target
    assert decode_embedded_url(embedded(target).replace("/rss/articles/", "/articles/")) == target
    assert decode_embedded_url(embedded(target).replace("/rss/articles/", "/read/")) == target


@pytest.mark.parametrize(
    "url",
    [
        "",
        "https://example.com/article",
        "ftp://news.google.com/article",
        "https://user:password@news.google.com/rss/articles/id",
        "https://[broken",
        "https://news.google.com:invalid/rss/articles/id",
        "https://news.google.com/rss/articles/id space",
        "https://news.google.com/rss/articles/" + "a" * 2100,
        "https://news.google.com/?articles=x",
        "https://news.google.com/rss/articles/A",
        envelope(b"random bytes"),
        envelope(b'\x08\x13"'),
        envelope(b'\x08\x13"\xff\xff\xff\xff\xff\x7f'),
        envelope(b'\x08\x13"\x00'),
        envelope(b'\x08\x13"\x14short'),
        envelope(b'\x08\x13"\x01\xff'),
        embedded("AU_yqLopaque-id"),
        embedded("javascript:alert(1)"),
        embedded("https://user:pass@example.com/a"),
        embedded("https://example.com:8000/a"),
        embedded("https://example.com/a\x00b"),
        embedded("https://example.com/a" + chr(92) + "b"),
    ],
)
def test_invalid_or_opaque_envelopes_are_not_decoded(url: str) -> None:
    assert decode_embedded_url(url) is None


async def test_resolver_checks_public_host_before_returning_a_decoded_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    async def guard(url: str) -> str:
        seen.append(url)
        if "private.example" in url:
            raise FeedFetchError("Resolves to private space")
        return "93.184.216.34"

    monkeypatch.setattr(google_news_links, "assert_public_host", guard)
    resolver = GoogleNewsUrlResolver()
    assert await resolver.resolve(embedded("https://example.com/a")) == "https://example.com/a"
    assert await resolver.resolve(embedded("https://private.example/a")) is None
    assert await resolver.resolve(embedded("AU_yqLopaque")) is None
    assert len(seen) == 2


async def test_resolver_rejects_literal_private_host_without_network() -> None:
    assert await GoogleNewsUrlResolver().resolve(embedded("http://127.0.0.1/admin")) is None


def evidence(label: str, url: str | None) -> EvidenceItem:
    item = EvidenceItem.from_event(
        label, make_event(label), NOW, source_name="Google News", independence_key="google"
    )
    return replace(item, url=url)


class RecordingResolver:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def resolve(self, url: str) -> str | None:
        self.calls.append(url)
        if url.endswith("error"):
            raise ValueError("Bad upstream response")
        if url.endswith("timeout"):
            raise TimeoutError()
        if url.endswith("opaque"):
            return None
        return "https://example.com/resolved"


async def test_only_cited_items_resolve_deduplicated_with_original_failures_retained() -> None:
    original = (
        evidence("E1", "https://news.google.com/shared"),
        evidence("E2", "https://news.google.com/shared"),
        evidence("E3", "https://news.google.com/uncited"),
        evidence("E4", "https://news.google.com/error"),
        evidence("E5", None),
        evidence("E6", "https://news.google.com/opaque"),
        evidence("E7", "https://news.google.com/timeout"),
    )
    resolver = RecordingResolver()
    result = await resolve_cited_links(resolver, original, {"E1", "E2", "E4", "E5", "E6", "E7"})
    assert result[0].url == result[1].url == "https://example.com/resolved"
    assert result[2:] == original[2:]
    assert original[0].url == "https://news.google.com/shared"
    assert result[0].content_hash == original[0].content_hash
    assert resolver.calls == [
        "https://news.google.com/shared",
        "https://news.google.com/error",
        "https://news.google.com/opaque",
        "https://news.google.com/timeout",
    ]


async def test_resolution_caps_unique_urls_and_propagates_shutdown() -> None:
    items = tuple(
        evidence(f"E{i}", f"https://news.google.com/{i}") for i in range(MAX_RESOLVED_LINKS + 5)
    )
    resolver = RecordingResolver()
    result = await resolve_cited_links(resolver, items, {item.label for item in items})
    assert len(resolver.calls) == MAX_RESOLVED_LINKS
    assert result[-1] == items[-1]

    class CancelledResolver:
        async def resolve(self, url: str) -> str | None:
            raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        await resolve_cited_links(CancelledResolver(), items, {"E0"})


async def test_resolution_stops_with_original_links_when_total_budget_expires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resolve_links, "RESOLUTION_BUDGET_SECONDS", 0.001)

    class SlowResolver:
        calls = 0

        async def resolve(self, url: str) -> str | None:
            self.calls += 1
            await asyncio.Event().wait()
            return None

    resolver = SlowResolver()
    items = (
        evidence("E1", "https://news.google.com/a"),
        evidence("E2", "https://news.google.com/b"),
    )
    assert await resolve_cited_links(resolver, items, {"E1", "E2"}) == items
    assert resolver.calls == 1
