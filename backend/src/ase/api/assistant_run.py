"""Cancel transient chat work on disconnect, timeout or request cancellation."""

import asyncio
from collections.abc import Awaitable, Callable

from fastapi import Request

from ase.domain.assistant import AssistantAnswer
from ase.domain.errors import InvalidRequest

ANSWER_SECONDS = 120


async def _disconnect(request: Request) -> None:
    while (await request.receive())["type"] != "http.disconnect":
        pass


async def run_answer(
    request: Request,
    operation: Callable[[], Awaitable[AssistantAnswer]],
) -> AssistantAnswer:
    # The request body has been parsed before this watcher reads the ASGI channel.
    work = asyncio.ensure_future(operation())
    watcher = asyncio.create_task(_disconnect(request))
    try:
        done, _ = await asyncio.wait(
            (work, watcher),
            timeout=ANSWER_SECONDS,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if watcher in done:
            watcher.result()
            raise InvalidRequest("The assistant request was disconnected.")
        if work in done:
            return work.result()
        raise InvalidRequest("The assistant timed out. No alternative model was used.")
    except TimeoutError:
        raise InvalidRequest("The assistant timed out. No alternative model was used.") from None
    finally:
        work.cancel()
        watcher.cancel()
        await asyncio.gather(work, watcher, return_exceptions=True)
