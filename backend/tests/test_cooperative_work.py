"""Cancellation joins workers and consumes failures without changing the outcome."""

import asyncio
import threading
from unittest.mock import Mock

import pytest

from ase.application.feeds.cooperative_work import joined_thread_call


async def test_repeated_cancellation_preserves_cancelled_error_when_worker_fails():
    entered, release = threading.Event(), threading.Event()

    def failing_work():
        entered.set()
        assert release.wait(3)
        raise ValueError("worker failed after cancellation")

    loop = asyncio.get_running_loop()
    previous = loop.get_exception_handler()
    handler = Mock()
    loop.set_exception_handler(handler)
    try:
        task = asyncio.create_task(joined_thread_call(failing_work))
        while not entered.is_set():
            await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert task.cancelled()
        await asyncio.sleep(0)
        handler.assert_not_called()
    finally:
        release.set()
        loop.set_exception_handler(previous)


async def test_uncancelled_worker_failure_still_propagates():
    def failing_work():
        raise ValueError("worker failed")

    with pytest.raises(ValueError, match="worker failed"):
        await joined_thread_call(failing_work)
