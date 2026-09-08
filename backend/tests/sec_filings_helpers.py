"""Network-free SEC fixture with canonical paths and a truthful test contact."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.feeds.http import FeedHttpClient
from ase.adapters.research_records.sec_client import SecClient

CIK = "0000001234"
INDEX = f"https://data.sec.gov/submissions/CIK{CIK}.json"
ARCHIVE = f"CIK{CIK}-submissions-001.json"
DOCUMENT = "https://www.sec.gov/Archives/edgar/data/1234/000099999926000001/filing.htm"
CONTENT = b"<html><body><p>The issuer reported revenue of GBP 12 million.</p></body></html>"


def columns(count: int = 1, *, filed: str = "2026-08-31") -> dict[str, Any]:
    return {
        "accessionNumber": [f"0000999999-26-{number + 1:06d}" for number in range(count)],
        "filingDate": [filed] * count,
        "form": ["10-K"] * count,
        "primaryDocument": ["filing.htm"] * count,
    }


def index(count: int = 1) -> dict[str, Any]:
    return {
        "cik": CIK,
        "name": "Synthetic Issuer",
        "filings": {
            "recent": columns(count),
            "files": [
                {
                    "name": ARCHIVE,
                    "filingFrom": "2025-01-01",
                    "filingTo": "2025-12-31",
                }
            ],
        },
    }


class SecTransport:
    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.responses: dict[str, Any] = {INDEX: index(), DOCUMENT: CONTENT}
        self.requests: list[httpx.Request] = []
        self.times: list[float] = []
        self.before: Callable[[httpx.Request], Awaitable[None]] | None = None

        async def guard(url: str) -> None:
            assert url.startswith(("https://data.sec.gov/", "https://www.sec.gov/"))

        async def respond(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            self.times.append(asyncio.get_running_loop().time())
            if self.before is not None:
                await self.before(request)
            body = self.responses[str(request.url)]
            if isinstance(body, httpx.Response):
                return body
            return (
                httpx.Response(200, content=body)
                if isinstance(body, bytes)
                else (httpx.Response(200, json=body))
            )

        monkeypatch.setattr(feed_http, "assert_public_host", guard)
        self.http = FeedHttpClient(
            "ASE fixture contact@example.com",
            client=httpx.AsyncClient(
                transport=httpx.MockTransport(respond),
            ),
        )
        self.client = SecClient(self.http)
