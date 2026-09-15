"""Repeated local scheduler startup cannot create duplicate admission loops."""

import asyncio

from ase.application.schedules.runner import ScheduleRunner


async def test_repeated_start_stop_keeps_one_loop_and_allows_restart() -> None:
    entered = asyncio.Event()
    sleeping = asyncio.Event()
    count = 0

    async def tick() -> int:
        nonlocal count
        count += 1
        entered.set()
        return 1

    async def blocked_sleep(_seconds: float) -> None:
        sleeping.set()
        await asyncio.Event().wait()

    runner = ScheduleRunner(tick, sleep=blocked_sleep)
    await runner.start()
    await runner.start()
    await asyncio.wait_for(sleeping.wait(), 1)
    assert count == 1
    await runner.stop()
    await runner.stop()

    entered.clear()
    sleeping.clear()
    await runner.start()
    await asyncio.wait_for(entered.wait(), 1)
    await runner.stop()
    assert count == 2
