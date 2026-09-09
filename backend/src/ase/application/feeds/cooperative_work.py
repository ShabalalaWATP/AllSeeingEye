"""Keep admission held until off-loop pure work finishes, including cancellation."""

import asyncio
import contextlib
from collections.abc import Callable


async def joined_thread_call[T](work: Callable[[], T]) -> T:
    worker = asyncio.create_task(asyncio.to_thread(work))
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        while not worker.done():
            try:
                await asyncio.shield(worker)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        # Cancellation remains the caller's outcome even if the worker fails.
        # Retrieve an already-completed failure too, avoiding orphaned task errors.
        with contextlib.suppress(asyncio.CancelledError, Exception):
            worker.result()
        raise
