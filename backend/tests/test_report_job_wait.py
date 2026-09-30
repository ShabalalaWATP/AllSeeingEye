"""A progressing worker may run longer than the idle budget; stalled work may not."""

import asyncio

import pytest

from report_job_wait import wait_for_progress


async def test_committed_progress_renews_the_idle_budget():
    progress = 0

    async def worker():
        nonlocal progress
        for _ in range(8):
            await asyncio.sleep(0.01)
            progress += 1

    async def snapshot():
        return {"job": progress}

    task = asyncio.create_task(worker())
    await wait_for_progress({"job": task}, snapshot, idle_timeout=0.05, poll_interval=0.005)
    assert progress == 8


async def test_idle_worker_is_cancelled_even_while_another_worker_progresses():
    progress = 0
    cancelled = asyncio.Event()

    async def stalled():
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    async def snapshot():
        nonlocal progress
        progress += 1
        return {"stalled": "same-payload", "active": progress}

    tasks = {"stalled": asyncio.create_task(stalled()), "active": asyncio.create_task(stalled())}
    with pytest.raises(TimeoutError, match="no committed checkpoint"):
        await wait_for_progress(tasks, snapshot, idle_timeout=0.02, poll_interval=0.005)
    assert cancelled.is_set()
    assert all(task.done() for task in tasks.values())


async def test_overall_cap_stops_endless_progress():
    progress = 0

    async def snapshot():
        nonlocal progress
        progress += 1
        return {"job": progress}

    task = asyncio.create_task(asyncio.Event().wait())
    with pytest.raises(TimeoutError):
        await wait_for_progress({"job": task}, snapshot, overall_timeout=0.03, poll_interval=0.005)
    assert task.cancelled()


async def test_worker_failure_is_preserved():
    async def worker():
        raise ValueError("test worker failure")

    async def snapshot():
        return {"job": "same"}

    with pytest.raises(ValueError, match="test worker failure"):
        await wait_for_progress({"job": asyncio.create_task(worker())}, snapshot)


async def test_blocked_progress_query_is_capped_and_cancels_worker():
    async def snapshot():
        await asyncio.Event().wait()
        return {}

    task = asyncio.create_task(asyncio.Event().wait())
    with pytest.raises(TimeoutError):
        await wait_for_progress({"job": task}, snapshot, overall_timeout=0.02)
    assert task.cancelled()
