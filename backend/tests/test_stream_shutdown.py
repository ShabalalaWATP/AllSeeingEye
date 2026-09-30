"""Server shutdown completes SSE framing; disconnection still cancels idle work."""

import asyncio

import pytest
from sse_starlette.sse import EventSourceResponse

from ase.api.routers import stream as stream_router
from helpers import USER_PASSWORD, login_token


@pytest.mark.parametrize("ending", ["shutdown", "disconnect", "cancel"])
async def test_idle_stream_ends_and_releases_resources(
    client, container, user, monkeypatch, ending
):
    token = await login_token(client, user.email, USER_PASSWORD)
    response = await stream_router.stream(user, container.issuer.verify(token), container)
    hello = asyncio.Event()
    stopping = asyncio.Event()
    disconnected = asyncio.Event()
    messages = []

    async def exit_signal():
        await stopping.wait()

    monkeypatch.setattr(EventSourceResponse, "_listen_for_exit_signal", staticmethod(exit_signal))

    async def receive():
        await disconnected.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)
        if b"event: hello" in message.get("body", b""):
            hello.set()

    running = asyncio.create_task(response({"type": "http"}, receive, send))
    try:
        async with asyncio.timeout(1):
            await hello.wait()
        assert container.bus.subscriber_count == 1
        assert container.streams.held(user.id) == 1
        if ending == "shutdown":
            stopping.set()
        elif ending == "disconnect":
            disconnected.set()
        else:
            running.cancel()
        async with asyncio.timeout(1):
            if ending == "cancel":
                with pytest.raises(asyncio.CancelledError):
                    await running
            else:
                await running
    finally:
        running.cancel()
        await asyncio.gather(running, return_exceptions=True)

    assert container.bus.subscriber_count == 0
    assert container.streams.held(user.id) == 0
    if ending == "shutdown":
        terminal = [
            message
            for message in messages
            if message["type"] == "http.response.body" and not message.get("more_body", False)
        ]
        assert terminal == [{"type": "http.response.body", "body": b"", "more_body": False}]
