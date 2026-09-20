"""Slow regional providers cannot discard successful traffic or starve later areas."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

from ase.adapters.feeds.adsb_global import AdsbGlobalConnector
from ase.adapters.feeds.adsb_watch import AdsbAreaConnector, WatchArea
from ase.adapters.feeds.http import FeedFetchError, FeedHttpStatusError
from ase.adapters.feeds.http_contracts import FeedRateLimitedError
from ase.application.ports.feed_diagnostics import DiagnosticFeedConnector
from feeds_helpers import NOW, FakeClock

AREAS = [WatchArea(str(i), str(i), i, 0, 250) for i in range(4)]


class SlowRegions:
    def __init__(self):
        self.requests = []
        self.cancelled = 0

    async def get_json(self, url, *, conditional=True):
        self.requests.append(url)
        if url in (AREAS[1].url, AREAS[2].url):
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                self.cancelled += 1
                raise
        return {"ac": [{"hex": "abc123", "lat": 1, "lon": 2, "seen_pos": 1}]}


async def test_slow_regions_keep_partial_batch_and_resume_after_last_attempt(monkeypatch):
    monkeypatch.setattr("ase.adapters.feeds.adsb_watch.AREA_FETCH_BUDGET_SECONDS", 0.1)
    monkeypatch.setattr("ase.adapters.feeds.adsb_watch.AREA_REQUEST_TIMEOUT_SECONDS", 0.06)
    http = SlowRegions()
    connector = AdsbAreaConnector(http, FakeClock(NOW), AREAS)
    async with asyncio.timeout(1):
        events = await connector.fetch()
    assert len(events) == 1
    assert isinstance(connector, DiagnosticFeedConnector)
    assert "Partial regional coverage: 1/4" in connector.warning
    assert http.cancelled == 2
    first_count = len(http.requests)
    await connector.fetch()
    assert http.requests[first_count] == AREAS[3].url


async def test_external_cancellation_propagates_and_does_not_return_success(monkeypatch):
    http = SlowRegions()
    connector = AdsbAreaConnector(http, FakeClock(NOW), AREAS[1:])
    task = asyncio.create_task(connector.fetch())
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert http.cancelled == 1


async def test_all_failed_regions_report_failure_without_claiming_success(monkeypatch):
    monkeypatch.setattr("ase.adapters.feeds.adsb_watch.AREA_REQUEST_TIMEOUT_SECONDS", 0.01)
    with pytest.raises(FeedFetchError, match="no successful"):
        await AdsbAreaConnector(SlowRegions(), FakeClock(NOW), AREAS[1:3]).fetch()


async def test_successful_empty_poll_replaces_failure_with_explicit_empty_status(monkeypatch):
    monkeypatch.setattr("ase.adapters.feeds.adsb_watch.AREA_REQUEST_TIMEOUT_SECONDS", 0.01)
    http = SlowRegions()
    connector = AdsbAreaConnector(http, FakeClock(NOW), AREAS[:2])
    await connector.fetch()
    assert connector.warning

    async def available(url, *, conditional=True):
        return {"ac": []}

    http.get_json = available
    assert await connector.fetch() == []
    assert "queries succeeded" in connector.warning
    assert "failed" not in connector.warning


@pytest.mark.parametrize("status", [403, 429, 503, "secret-status", True, 999])
async def test_http_diagnostics_keep_only_valid_numeric_codes(status):

    http = AsyncMock()
    http.get_json.side_effect = FeedHttpStatusError(status, "https://private/?key=secret")
    connector = AdsbAreaConnector(http, FakeClock(NOW), AREAS[:2])
    with pytest.raises(FeedFetchError) as captured:
        await connector.fetch()
    diagnostic = str(captured.value) + connector.warning
    assert "2 failed queries" in diagnostic
    assert "secret" not in diagnostic and "https" not in diagnostic
    if type(status) is int and 100 <= status <= 599:
        assert f"{status} (2)" in diagnostic
    else:
        assert "HTTP statuses" not in diagnostic


async def test_global_warning_retains_partial_http_failure_counts():

    http = AsyncMock()
    http.get_json.side_effect = [
        FeedHttpStatusError(429, "https://private/?key=secret"),
        *[{"ac": []} for _ in range(23)],
    ]
    connector = AdsbGlobalConnector(http, FakeClock(NOW))
    connector._request_interval = 0
    assert await connector.fetch() == []
    assert "Sampled worldwide sweep" in connector.coverage_warning
    assert "23/24 areas retrieved" in connector.warning
    assert "1 failed queries" in connector.warning
    assert "429 (1)" in connector.warning
    assert "secret" not in connector.warning


async def test_throttled_batch_retains_successes_and_resumes_after_last_attempt():
    http = AsyncMock()
    http.get_json.side_effect = [
        {"ac": [{"hex": "abc123", "lat": 1, "lon": 2, "seen_pos": 1}]},
        FeedRateLimitedError(AREAS[1].url, timedelta(seconds=90)),
        {"ac": []},
        {"ac": []},
        {"ac": []},
        {"ac": []},
    ]
    connector = AdsbAreaConnector(http, FakeClock(NOW), AREAS)
    assert len(await connector.fetch()) == 1
    assert http.get_json.await_count == 2
    assert "1/4 areas retrieved" in connector.warning
    assert "2 unattempted" in connector.warning
    assert "429 (1)" in connector.warning
    await connector.fetch()
    assert http.get_json.await_args_list[2].args == (AREAS[2].url,)


async def test_entirely_throttled_batch_preserves_scheduler_backoff():
    http = AsyncMock()
    http.get_json.side_effect = FeedRateLimitedError(AREAS[0].url, timedelta(seconds=90))
    connector = AdsbAreaConnector(http, FakeClock(NOW), AREAS)
    with pytest.raises(FeedRateLimitedError) as caught:
        await connector.fetch()
    assert caught.value.retry_after == timedelta(seconds=90)
    assert http.get_json.await_count == 1
