"""A stream slot is returned exactly once, even when the body generator never starts."""

import asyncio

import pytest
from sse_starlette.sse import EventSourceResponse

from ase.api.routers import stream as stream_router
from ase.api.stream_slot import ReleaseOnce
from helpers import USER_PASSWORD, login_token


def _no_exit_signal(monkeypatch) -> None:
    async def exit_signal():
        await asyncio.Event().wait()

    monkeypatch.setattr(EventSourceResponse, "_listen_for_exit_signal", staticmethod(exit_signal))


async def _open(client, container, user):
    token = await login_token(client, user.email, USER_PASSWORD)
    return await stream_router.stream(user, container.issuer.verify(token), container)


async def test_disconnect_before_the_first_iteration_releases_the_slot(
    client, container, user, monkeypatch
):
    response = await _open(client, container, user)
    assert container.streams.held(user.id) == 1
    never = asyncio.Event()
    _no_exit_signal(monkeypatch)
    sent: list[dict] = []

    async def receive():
        return {"type": "http.disconnect"}  # the client is already gone

    async def send(message):
        sent.append(message)
        await never.wait()  # the response start never completes

    async with asyncio.timeout(1):
        await response({"type": "http"}, receive, send)

    # The generator was never iterated, so its own `finally` could not release the slot.
    assert [message["type"] for message in sent] == ["http.response.start"]
    assert container.bus.subscriber_count == 0
    assert container.streams.held(user.id) == 0


async def test_a_consumed_stream_releases_its_slot_only_once(client, container, user, monkeypatch):
    _no_exit_signal(monkeypatch)
    first = await _open(client, container, user)
    second = await _open(client, container, user)
    assert container.streams.held(user.id) == 2
    frames = first.body_iterator
    async with asyncio.timeout(1):
        assert (await anext(frames))["event"] == "hello"  # type: ignore[call-overload]
    await frames.aclose()  # type: ignore[attr-defined]
    assert container.streams.held(user.id) == 1

    async def receive():
        return {"type": "http.disconnect"}

    async def send(_message):
        return None

    # Running the finished response must not release the second stream's slot as well.
    async with asyncio.timeout(1):
        await first({"type": "http"}, receive, send)
    assert container.streams.held(user.id) == 1
    await second.body_iterator.aclose()  # type: ignore[attr-defined]
    async with asyncio.timeout(1):
        await second({"type": "http"}, receive, send)
    assert container.streams.held(user.id) == 0


async def test_a_failure_before_the_response_exists_releases_the_slot(
    client, container, user, monkeypatch
):
    def broken(*_args, **_kwargs):
        raise RuntimeError("could not build the stream")

    monkeypatch.setattr(stream_router, "LiveStream", broken)
    with pytest.raises(RuntimeError):
        await _open(client, container, user)
    assert container.streams.held(user.id) == 0


def test_release_once_is_idempotent() -> None:
    calls: list[int] = []
    release = ReleaseOnce(lambda: calls.append(1))
    assert not release.released
    release()
    release()
    assert calls == [1] and release.released
