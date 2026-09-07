"""Bounded polling survives transient failures and stops cleanly on cancellation."""

import asyncio
from uuid import uuid4

import pytest

from ase.application.reports.monitor_runner import AnnotationMonitorWorker


async def test_cycle_failure_recovers_without_private_logging_and_cancellation_propagates(caplog):
    calls, observed, sleeps = [], [], []
    key = uuid4()

    async def due(limit, after):
        calls.append((limit, after))
        if len(calls) == 1:
            raise RuntimeError("private source text must not leak")
        return [key]

    async def observe(key):
        observed.append(key)
        return True

    async def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise asyncio.CancelledError()

    worker = AnnotationMonitorWorker(due, observe, sleep=sleep)
    with pytest.raises(asyncio.CancelledError):
        await worker.run()
    assert observed == [key] and sleeps == [5, 5]
    assert "private source text" not in caplog.text


async def test_worker_pages_fairly_and_continues_after_one_monitor_error():
    ids = sorted([uuid4() for _ in range(21)])
    pages, observed = [], []

    async def due(limit, after):
        pages.append((limit, after))
        return [key for key in ids if after is None or key > after][:limit]

    async def observe(key):
        observed.append(key)
        if key == ids[0]:
            raise RuntimeError("temporary")
        return True

    worker = AnnotationMonitorWorker(due, observe)
    assert await worker.run_once() == 19
    assert await worker.run_once() == 1
    assert observed == ids and pages == [(20, None), (20, ids[19])]
    assert worker.cursor is None
