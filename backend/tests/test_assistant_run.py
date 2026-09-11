"""Transient request work and its disconnect watcher must always be cancelled and joined."""

import asyncio

import pytest
from starlette.requests import Request

import ase.api.assistant_run as runner
from ase.api.assistant_run import run_answer
from ase.domain.assistant import (
    AssistantAnswer,
    AssistantContext,
    AssistantParagraph,
    AssistantQuestion,
)
from ase.domain.errors import InvalidRequest
from assistant_helpers import NOW


def answer():
    return AssistantAnswer(
        (AssistantParagraph("gap", "No matching observations."),),
        AssistantContext((), 0, 0, False, ()),
        AssistantQuestion("Overview"),
        NOW,
    )


class Incoming:
    def __init__(self):
        self.started = asyncio.Event()
        self.stopped = asyncio.Event()
        self.messages = asyncio.Queue()
        self.error = None

    async def receive(self):
        self.started.set()
        try:
            item = await self.messages.get()
            if self.error is not None:
                raise self.error
            return item
        finally:
            self.stopped.set()

    def request(self):
        return Request(
            {"type": "http", "method": "POST", "path": "/api/assistant/answer"}, self.receive
        )


@pytest.mark.parametrize("kind", ["disconnect", "timeout", "cancel"])
async def test_request_interruptions_cancel_and_join_work(kind, monkeypatch):
    started, cleaned = asyncio.Event(), asyncio.Event()
    incoming = Incoming()

    async def operation():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            # A scheduled cleanup proves run_answer waits for cancellation completion.
            await asyncio.sleep(0)
            cleaned.set()

    monkeypatch.setattr(runner, "ANSWER_SECONDS", 0.02 if kind == "timeout" else 5)
    task = asyncio.create_task(run_answer(incoming.request(), operation))
    await asyncio.wait_for(started.wait(), timeout=1)
    if kind == "disconnect":
        incoming.messages.put_nowait({"type": "http.disconnect"})
    elif kind == "cancel":
        task.cancel()
    with pytest.raises(asyncio.CancelledError if kind == "cancel" else InvalidRequest) as error:
        await asyncio.wait_for(task, timeout=1)
    assert cleaned.is_set() and incoming.stopped.is_set()
    if kind == "timeout":
        assert "timed out" in str(error.value) and "No alternative model" in str(error.value)


async def test_success_returns_same_answer_and_joins_disconnect_watcher():
    incoming = Incoming()
    expected = answer()

    async def operation():
        await incoming.started.wait()
        return expected

    actual = await run_answer(incoming.request(), operation)
    assert actual is expected
    assert incoming.stopped.is_set()


@pytest.mark.parametrize("error", [InvalidRequest("Safe failure"), TimeoutError()])
async def test_operation_errors_join_watcher_and_provider_timeout_is_safe(error):
    incoming = Incoming()

    async def operation():
        await incoming.started.wait()
        raise error

    with pytest.raises(InvalidRequest) as raised:
        await run_answer(incoming.request(), operation)
    assert incoming.stopped.is_set()
    if isinstance(error, TimeoutError):
        assert "timed out" in str(raised.value)
    else:
        assert raised.value is error


async def test_watcher_skips_remaining_body_messages_until_actual_disconnect():
    incoming = Incoming()
    cleaned = asyncio.Event()

    async def operation():
        await incoming.started.wait()
        incoming.messages.put_nowait({"type": "http.request", "body": b"", "more_body": False})
        incoming.messages.put_nowait({"type": "http.disconnect"})
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    with pytest.raises(InvalidRequest, match="disconnected"):
        await run_answer(incoming.request(), operation)
    assert cleaned.is_set() and incoming.messages.empty()


async def test_broken_receive_channel_cancels_work_without_returning_partial_answer():
    incoming = Incoming()
    incoming.error = RuntimeError("Receive channel closed unexpectedly")
    cleaned = asyncio.Event()

    async def operation():
        await incoming.started.wait()
        incoming.messages.put_nowait({"type": "http.disconnect"})
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    with pytest.raises(RuntimeError, match="Receive channel"):
        await run_answer(incoming.request(), operation)
    assert cleaned.is_set() and incoming.stopped.is_set()
