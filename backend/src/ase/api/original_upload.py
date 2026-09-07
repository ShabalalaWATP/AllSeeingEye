"""Cancel post-intake retention when an upload client disconnects."""

import asyncio
from collections.abc import Coroutine
from typing import Any

from fastapi import Request

from ase.domain.original_assets import OriginalAsset


async def finish_connected(
    request: Request,
    operation: Coroutine[Any, Any, OriginalAsset],
) -> OriginalAsset:
    async def disconnected() -> None:
        while (await request.receive())["type"] != "http.disconnect":
            pass

    work = asyncio.create_task(operation)
    watcher = asyncio.create_task(disconnected())
    try:
        done, _ = await asyncio.wait((work, watcher), return_when=asyncio.FIRST_COMPLETED)
        if watcher in done:
            raise asyncio.CancelledError()
        return await work
    finally:
        for task in (work, watcher):
            if not task.done():
                task.cancel()
        await asyncio.gather(work, watcher, return_exceptions=True)
