"""A disconnect watcher must remain cancellable while the response is being prepared."""

import asyncio

import pytest

from ase.api.report_run import _disconnect


async def test_watcher_cancellation_does_not_depend_on_polling_cancel_scopes():
    entered = asyncio.Event()

    class RequestBoundary:
        async def receive(self):
            entered.set()
            await asyncio.Event().wait()

        async def is_disconnected(self):
            # Starlette's polling API has its own cancelled AnyIO scope. An outer
            # task cancellation can be consumed at this boundary instead of stopping
            # the watcher. Model that observed failure without a timing-dependent race.
            entered.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                return False

    task = asyncio.create_task(_disconnect(RequestBoundary()))
    await entered.wait()
    task.cancel()
    try:
        done, _ = await asyncio.wait((task,), timeout=0.05)
        assert task in done, "Report response must not wait indefinitely for its disconnect watcher"
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_watcher_consumes_remaining_body_messages_until_disconnect():
    messages = asyncio.Queue()
    messages.put_nowait({"type": "http.request", "body": b"", "more_body": False})
    messages.put_nowait({"type": "http.disconnect"})

    class RequestBoundary:
        async def receive(self):
            return await messages.get()

    await asyncio.wait_for(_disconnect(RequestBoundary()), timeout=0.1)
    assert messages.empty()
