"""Owned, network-free fixtures for bounded public-record collection."""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedHttpClient
from ase.domain.research import ResearchFocus, ResearchQuery
from feeds_helpers import FakeClock

CLOCK = FakeClock(datetime(2026, 9, 6, 12, tzinfo=UTC))
QUERY = ResearchQuery(
    question="Private analytical question which must not appear in the request",
    since=datetime(2026, 9, 5, tzinfo=UTC),
    until=datetime(2026, 9, 6, tzinfo=UTC),
)

COMPANY = replace(QUERY, focus=ResearchFocus.COMPANY, subject="CIK 1234")
DOMAIN = replace(QUERY, focus=ResearchFocus.DOMAIN, subject="example.com")


class RecordService:
    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        data: Any = None,
        *,
        response: httpx.Response | None = None,
        max_bytes: int = 20000,
    ) -> None:
        self.requests: list[httpx.Request] = []
        self.guarded: list[str] = []

        async def guard(url: str) -> None:
            self.guarded.append(url)

        def respond(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return response if response is not None else httpx.Response(200, json=data)

        monkeypatch.setattr(feed_http, "assert_public_host", guard)
        self.http = FeedHttpClient(
            "ASE tests contact@example.test",
            max_bytes=max_bytes,
            client=httpx.AsyncClient(transport=httpx.MockTransport(respond)),
        )


def submissions(count: int = 1) -> dict[str, Any]:
    return {
        "cik": "0000001234",
        "name": "Example Company",
        "filings": {
            "recent": {
                "accessionNumber": [f"0000001234-26-{index:06d}" for index in range(count)],
                "filingDate": ["2026-09-05"] * count,
                "form": ["10-K"] * count,
            },
            "files": [{"name": "https://127.0.0.1/should-not-fetch"}],
        },
    }


def dns_payload(record_type: int = 1, answers: list[Any] | None = None) -> dict[str, Any]:
    return {
        "Status": 0,
        "AD": True,
        "Question": [{"name": "example.com.", "type": record_type}],
        "Answer": answers
        if answers is not None
        else [{"name": "example.com.", "type": record_type, "data": "192.0.2.1"}],
    }


__all__ = ["CLOCK", "COMPANY", "DOMAIN", "RecordService", "dns_payload", "submissions"]
