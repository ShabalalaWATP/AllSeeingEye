"""Cancelling a poll must not leave untracked or reordered disk writes."""

import asyncio
import json
import threading
from datetime import timedelta
from pathlib import Path

import pytest

from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.feeds.satellites import ACTIVE_SATELLITES, SatelliteConnector
from feeds_helpers import NOW, FakeClock, FakeHttp
from test_pipeline_and_scheduler import build_scheduler


def slow_cache(connector, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    cache = connector._catalogue.cache
    original = cache.save
    active = {"current": 0, "maximum": 0}

    def save(state):
        active["current"] += 1
        active["maximum"] = max(active["maximum"], active["current"])
        entered.set()
        try:
            assert release.wait(5), "Test did not release the cache writer"
            original(state)
        finally:
            active["current"] -= 1

    monkeypatch.setattr(cache, "save", save)
    return entered, release, active, cache.path


async def test_repeated_cancellation_holds_lock_until_disk_write_finishes(tmp_path, monkeypatch):
    http = FakeHttp()
    connector = SatelliteConnector(http, FakeClock(NOW), ACTIVE_SATELLITES, cache_dir=tmp_path)
    entered, release, active, path = slow_cache(connector, monkeypatch)
    first = asyncio.create_task(connector.fetch())
    try:
        assert await asyncio.to_thread(entered.wait, 2)
        first.cancel()
        second = asyncio.create_task(connector.fetch())
        await asyncio.sleep(0)
        first.cancel()
        await asyncio.sleep(0)
        assert not first.done() and not second.done()
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await first
    with pytest.raises(FeedFetchError, match="incomplete"):
        await second
    assert active == {"current": 0, "maximum": 1}
    assert json.loads(path.read_bytes())["retry_at"] == (NOW + timedelta(hours=2)).isoformat()
    assert not http.requests


async def test_retry_then_shutdown_awaits_retiring_cache_writer(tmp_path: Path, monkeypatch):
    clock = FakeClock(NOW)
    connector = SatelliteConnector(FakeHttp(), clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    scheduler, _, _, _ = build_scheduler([connector], clock)
    entered, release, active, _ = slow_cache(connector, monkeypatch)
    first = asyncio.create_task(connector.fetch())
    scheduler._tasks[ACTIVE_SATELLITES.id] = first
    scheduler._prune_task = asyncio.create_task(asyncio.sleep(60))
    try:
        assert await asyncio.to_thread(entered.wait, 2)
        scheduler.resume(ACTIVE_SATELLITES.id)
        assert first in scheduler._retiring_tasks
        stopping = asyncio.create_task(scheduler.stop())
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert not stopping.done()
    finally:
        release.set()
    await stopping
    assert first.done()
    assert active["current"] == 0
    assert not scheduler._tasks and not scheduler._retiring_tasks


async def test_failed_writer_cannot_replace_cancellation_and_restart_old_poll(
    tmp_path, monkeypatch
):
    entered, release = threading.Event(), threading.Event()
    connector = SatelliteConnector(
        FakeHttp(), FakeClock(NOW), ACTIVE_SATELLITES, cache_dir=tmp_path
    )

    def failed_save(state):
        entered.set()
        assert release.wait(5)
        raise OSError("Disk became unavailable")

    monkeypatch.setattr(connector._catalogue.cache, "save", failed_save)
    poll = asyncio.create_task(connector.fetch())
    try:
        assert await asyncio.to_thread(entered.wait, 2)
        poll.cancel()
        await asyncio.sleep(0)
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await poll
    assert poll.cancelled()
