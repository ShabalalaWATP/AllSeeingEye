"""An unexpected exception costs one scheduler cycle, never the loop; cancellation still ends it."""

import asyncio
import logging

import pytest

from ase.adapters.worker_health import InMemoryWorkerHeartbeats
from ase.application.worker_progress import worker_heartbeats
from test_feed_scheduler_reliability import connector, scheduler_for

SECRET = "https://feeds.example/rss?token=do-not-log"


class StopAfter:
    """A fake sleep that records each wait and cancels the loop at the given call."""

    def __init__(self, calls: int) -> None:
        self.waits: list[float] = []
        self._calls = calls

    async def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)
        if len(self.waits) >= self._calls:
            raise asyncio.CancelledError


async def test_a_failing_poll_cycle_does_not_end_the_source_loop(monkeypatch, caplog) -> None:
    source = connector("survivor")
    sleep = StopAfter(4)
    scheduler, _store = scheduler_for([source], sleep=sleep, jitter=0.0)
    original = scheduler.poller.poll_once
    polls = 0

    async def poll(target):
        nonlocal polls
        polls += 1
        if polls == 1:
            raise RuntimeError(f"unexpected failure for {SECRET}")
        return await original(target)

    monkeypatch.setattr(scheduler.poller, "poll_once", poll)
    caplog.set_level(logging.ERROR, logger="ase.application.feeds.scheduler")
    with pytest.raises(asyncio.CancelledError):
        await scheduler._run_connector(source, first_delay=0.0)

    assert polls == 3  # the loop kept polling after the failed cycle
    interval = source.spec.poll_interval.total_seconds()
    assert sleep.waits[:2] == [0.0, interval]  # a failed cycle waits one normal interval
    failures = [record for record in caplog.records if record.getMessage() == "feed_cycle_failed"]
    assert len(failures) == 1
    assert failures[0].error == "RuntimeError"  # type: ignore[attr-defined]
    assert failures[0].source_id == "survivor"  # type: ignore[attr-defined]
    assert "do-not-log" not in caplog.text


async def test_cancellation_inside_a_poll_is_not_swallowed(monkeypatch) -> None:
    source = connector("cancelled")
    sleep = StopAfter(10)
    scheduler, _store = scheduler_for([source], sleep=sleep)

    async def poll(_target):
        raise asyncio.CancelledError

    monkeypatch.setattr(scheduler.poller, "poll_once", poll)
    with pytest.raises(asyncio.CancelledError):
        await scheduler._run_connector(source, first_delay=0.0)
    assert sleep.waits == [0.0]


async def test_a_failing_prune_does_not_end_the_prune_loop(monkeypatch, caplog) -> None:
    sleep = StopAfter(4)
    scheduler, _store = scheduler_for([], sleep=sleep)
    prunes = 0

    async def prune() -> int:
        nonlocal prunes
        prunes += 1
        if prunes == 1:
            raise RuntimeError(f"prune failed near {SECRET}")
        return 0

    monkeypatch.setattr(scheduler.poller, "prune", prune)
    registry = InMemoryWorkerHeartbeats()
    token = worker_heartbeats.set(registry)
    caplog.set_level(logging.ERROR, logger="ase.application.feeds.scheduler")
    try:
        with pytest.raises(asyncio.CancelledError):
            await scheduler._prune_loop()
    finally:
        worker_heartbeats.reset(token)

    assert prunes == 3
    failures = [record for record in caplog.records if record.getMessage() == "feed_prune_failed"]
    assert [record.error for record in failures] == ["RuntimeError"]  # type: ignore[attr-defined]
    assert "do-not-log" not in caplog.text
    (state,) = [worker for worker in registry.snapshot() if worker.name == "scheduler"]
    assert state.last_cycle is not None
    assert state.last_error_code is None  # the later successful prune cleared the failure
