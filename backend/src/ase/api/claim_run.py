"""Keep claim generation in the parsed HTTP request's lifetime."""

import asyncio
from collections.abc import Coroutine
from typing import Any

from fastapi import HTTPException, Request

from ase.application.reports.generate_claims import ClaimGenerationResult


async def _disconnect(request: Request) -> None:
    while (await request.receive())["type"] != "http.disconnect":
        pass


async def run_claim_generation(
    request: Request, operation: Coroutine[Any, Any, ClaimGenerationResult]
) -> ClaimGenerationResult:
    work = asyncio.create_task(operation)
    watcher = asyncio.create_task(_disconnect(request))
    try:
        done, _ = await asyncio.wait(
            (work, watcher), timeout=60, return_when=asyncio.FIRST_COMPLETED
        )
        if work in done:
            return work.result()
        if watcher in done:
            watcher.result()
        raise HTTPException(
            499 if watcher in done else 504,
            "Claim generation interrupted. Check claim history before retrying if saving started.",
        )
    finally:
        for task in (work, watcher):
            if not task.done():
                task.cancel()
        # Await cancellation accounting before the request's database session closes.
        await asyncio.gather(work, watcher, return_exceptions=True)
