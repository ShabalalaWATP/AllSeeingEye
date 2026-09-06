"""Controlled public-feed responses for request-budget and provenance regressions."""

from datetime import UTC, datetime
from xml.sax.saxutils import escape

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedHttpClient
from ase.domain.research import ResearchQuery
from feeds_helpers import FakeClock

NOW = datetime(2026, 9, 6, 12, tzinfo=UTC)
CLOCK = FakeClock(NOW)
QUERY = ResearchQuery(
    question="Private analytical question which must not appear in the request",
    since=datetime(2026, 9, 5, tzinfo=UTC),
    until=datetime(2026, 9, 6, tzinfo=UTC),
    terms=("rail disruption",),
)


def item(
    key: str = "1",
    title: str = "Rail disruption at crossing",
    date: str = "2026-09-05T10:00:00Z",
    extra: str = "",
) -> str:
    return (
        f"<item><guid>{key}</guid><title>{escape(title)}</title>"
        f"<link>https://publisher.example/{key}</link><pubDate>{date}</pubDate>"
        f"<description>A report from the crossing.</description>{extra}</item>"
    )


def rss(items: str) -> str:
    return f"<rss><channel>{items}</channel></rss>"


class PublicFeed:
    def __init__(self, monkeypatch: pytest.MonkeyPatch, response: httpx.Response) -> None:
        self.requests: list[httpx.Request] = []
        self.guarded: list[str] = []

        async def guard(url: str) -> None:
            self.guarded.append(url)

        def respond(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return response

        monkeypatch.setattr(feed_http, "assert_public_host", guard)
        self.http = FeedHttpClient(
            "ASE test", client=httpx.AsyncClient(transport=httpx.MockTransport(respond))
        )
