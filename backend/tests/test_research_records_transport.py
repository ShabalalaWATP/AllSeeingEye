"""Transport failures consume no retry and cannot leak request or response details."""

import asyncio
from typing import Any

import httpx
import pytest

from ase.adapters.feeds import http as feed_http
from ase.adapters.research_records import DnsResearchProvider, SecSubmissionsProvider
from ase.domain.research import CollectionStatus
from research_records_helpers import CLOCK, COMPANY, DOMAIN, RecordService


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(302, headers={"Location": "https://other.example.com/leaked-secret"}),
        httpx.Response(503, text="secret failure details"),
        httpx.Response(304),
        httpx.Response(200, text="not-json leaked-secret"),
        httpx.Response(200, json=[]),
        httpx.Response(200, content=b"x" * 20001),
        httpx.Response(200, content=b"compressed", headers={"Content-Encoding": "unknown"}),
    ],
)
async def test_single_request_safe_failure_receipts(
    monkeypatch: pytest.MonkeyPatch,
    response: httpx.Response,
) -> None:
    service = RecordService(monkeypatch, response=response)
    batch = await SecSubmissionsProvider(service.http, CLOCK).collect(COMPANY)
    assert batch.attempts[0].status is CollectionStatus.FAILED
    assert len(service.requests) == len(service.guarded) == 1
    assert "secret" not in str(batch)
    assert "https://" not in batch.attempts[0].explanation
    assert COMPANY.question not in str(batch)
    await service.http.aclose()


async def test_collection_timeout_is_safe_and_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    service = RecordService(monkeypatch)
    calls = []

    async def timed_out(*args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        raise TimeoutError("secret timeout payload")

    monkeypatch.setattr(service.http, "get_json", timed_out)
    batch = await DnsResearchProvider(service.http, CLOCK).collect(DOMAIN)
    assert batch.attempts[0].status is CollectionStatus.TIMED_OUT
    assert len(calls) == 1
    assert calls[0][1] == {"conditional": False, "max_redirects": 0}
    assert "secret" not in str(batch)
    await service.http.aclose()


async def test_real_guard_blocks_private_api_resolution_before_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_guard = feed_http.assert_public_host
    service = RecordService(monkeypatch)
    monkeypatch.setattr(feed_http, "assert_public_host", real_guard)

    async def resolves_private(*args: Any, **kwargs: Any) -> list[tuple[Any, ...]]:
        return [(None, None, None, None, ("127.0.0.1", 0))]

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", resolves_private)
    batch = await DnsResearchProvider(service.http, CLOCK).collect(DOMAIN)
    assert batch.attempts[0].status is CollectionStatus.FAILED
    assert service.requests == []
    assert "127.0.0.1" not in str(batch)
    await service.http.aclose()
