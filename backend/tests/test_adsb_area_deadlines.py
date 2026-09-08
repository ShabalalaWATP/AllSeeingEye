"""Slow regional providers cannot discard successful traffic or starve later areas."""

import asyncio

import pytest

from ase.adapters.feeds.adsb_watch import AdsbAreaConnector, WatchArea
from ase.adapters.feeds.http import FeedFetchError
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


async def test_successful_next_poll_clears_partial_warning(monkeypatch):
    monkeypatch.setattr("ase.adapters.feeds.adsb_watch.AREA_REQUEST_TIMEOUT_SECONDS", 0.01)
    http = SlowRegions()
    connector = AdsbAreaConnector(http, FakeClock(NOW), AREAS[:2])
    await connector.fetch()
    assert connector.warning

    async def available(url, *, conditional=True):
        return {"ac": []}

    http.get_json = available
    assert await connector.fetch() == []
    assert connector.warning is None
