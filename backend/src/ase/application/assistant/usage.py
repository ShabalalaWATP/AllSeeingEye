"""One bounded bookkeeping writer, including cancellation during a model response."""

import asyncio
import time
from collections.abc import Awaitable, Callable

from ase.domain.llm import LlmUsage


async def save_usage(sink: Callable[[LlmUsage], Awaitable[None]], usage: LlmUsage) -> bool:
    pending = asyncio.ensure_future(sink(usage))
    deadline = time.perf_counter() + 3
    try:
        async with asyncio.timeout(3):
            await asyncio.shield(pending)
    except asyncio.CancelledError:
        try:
            async with asyncio.timeout(max(0, deadline - time.perf_counter())):
                await asyncio.shield(pending)
        except (Exception, asyncio.CancelledError):
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
        raise
    except Exception:
        pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)
        # A commit may have succeeded before close failed. Never retry this write.
        return False
    return True
