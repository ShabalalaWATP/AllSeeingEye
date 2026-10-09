"""Large map bodies have bounded admission and release capacity on every exit."""

import asyncio
from uuid import UUID

import pytest
from starlette.datastructures import Headers

from ase.api import map_body_admission
from ase.api.map_body_admission import MAP_VIEW_MAX_BODY_BYTES
from ase.api.middleware import BodySizeLimitMiddleware
from ase.domain.errors import InvalidRequest
from test_map_body_auth import SAVE_PATHS, map_scope


class Harness:
    def __init__(self):
        self.bodies = []
        self.processing = asyncio.Event()
        self.finish = asyncio.Event()
        self.finish.set()
        self.fail_after_start = False
        self.app = BodySizeLimitMiddleware(self.downstream)

    async def downstream(self, scope, receive, send):
        self.bodies.append((await receive())["body"])
        self.processing.set()
        await self.finish.wait()
        await send({"type": "http.response.start", "status": 204, "headers": []})
        if self.fail_after_start:
            raise InvalidRequest("Downstream failed")
        await send({"type": "http.response.body", "body": b""})

    async def request(self, user_id=1, receive=None, route=None, declared=None):
        method, path = route or SAVE_PATHS[0]
        scope = map_scope(method, path)
        scope["test_user_id"] = UUID(int=user_id)
        if declared is not None:
            scope["headers"].append((b"content-length", str(declared).encode()))
        messages = []

        async def send(message):
            messages.append(message)

        await self.app(scope, receive or small_body, send)
        return messages


async def small_body():
    return {"type": "http.request", "body": b"{}", "more_body": False}


async def forbidden_read():
    raise AssertionError("Admission rejection must not read the body")


@pytest.fixture
def harness(monkeypatch):
    async def authenticated(scope):
        return scope["test_user_id"]

    monkeypatch.setattr(map_body_admission, "authenticated_map_user", authenticated)
    return Harness()


@pytest.mark.parametrize(
    "route",
    SAVE_PATHS[1:],
)
async def test_one_account_cannot_fill_other_accounts_slots_or_bypass_with_patch(harness, route):
    reading = asyncio.Event()
    finish = asyncio.Event()

    async def stalled():
        reading.set()
        await finish.wait()
        return await small_body()

    pending = asyncio.create_task(harness.request(receive=stalled))
    try:
        await asyncio.wait_for(reading.wait(), 1)
        rejected = await harness.request(receive=forbidden_read, route=route)
        assert rejected[0]["status"] == 429
        assert Headers(scope=rejected[0])["retry-after"] == "1"
        assert Headers(scope=rejected[0])["cache-control"] == "no-store"
        assert (await harness.request(user_id=2))[0]["status"] == 204
    finally:
        finish.set()
        await pending
    assert (await harness.request())[0]["status"] == 204


async def test_global_admission_rejects_before_read_and_cancelled_saves_release_it(harness):
    reading = [asyncio.Event() for _ in range(map_body_admission.MAX_CONCURRENT_MAP_SAVES)]

    async def stalled(event):
        event.set()
        await asyncio.Event().wait()

    pending = [
        asyncio.create_task(harness.request(index + 1, lambda event=event: stalled(event)))
        for index, event in enumerate(reading)
    ]
    try:
        await asyncio.wait_for(asyncio.gather(*(event.wait() for event in reading)), 1)
        assert (await harness.request(99, forbidden_read))[0]["status"] == 429
    finally:
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
    assert (await harness.request(99))[0]["status"] == 204


async def test_slot_covers_downstream_parsing_and_persistence(harness):
    harness.finish.clear()
    pending = asyncio.create_task(harness.request())
    try:
        await asyncio.wait_for(harness.processing.wait(), 1)
        assert (await harness.request(receive=forbidden_read))[0]["status"] == 429
    finally:
        harness.finish.set()
        await pending
    assert (await harness.request())[0]["status"] == 204


@pytest.mark.parametrize("ending", ["disconnect", "cancel", "error"])
async def test_partial_body_is_discarded_and_slot_released_on_abnormal_exit(harness, ending):
    chunks = 0

    async def receive():
        nonlocal chunks
        chunks += 1
        if chunks == 1:
            return {"type": "http.request", "body": b"x" * 65536, "more_body": True}
        if ending == "disconnect":
            return {"type": "http.disconnect"}
        if ending == "cancel":
            raise asyncio.CancelledError
        raise RuntimeError("Receive failed")

    if ending == "disconnect":
        assert await harness.request(receive=receive) == []
    else:
        with pytest.raises(asyncio.CancelledError if ending == "cancel" else RuntimeError):
            await harness.request(receive=receive)
    assert harness.bodies == []
    assert (await harness.request())[0]["status"] == 204


@pytest.mark.parametrize("trickling", [False, True])
async def test_read_deadline_is_total_and_releases_capacity(harness, monkeypatch, trickling):
    monkeypatch.setattr(map_body_admission, "MAP_BODY_READ_TIMEOUT_SECONDS", 0.05)
    chunks = 0

    async def receive():
        nonlocal chunks
        chunks += 1
        if chunks > 1:
            if trickling:
                await asyncio.sleep(0.005)
            else:
                await asyncio.Event().wait()
        return {"type": "http.request", "body": b"x", "more_body": True}

    result = await asyncio.wait_for(harness.request(receive=receive), 1)
    assert result[0]["status"] == 422
    assert b"timed out" in result[1]["body"]
    assert harness.bodies == []
    assert (await harness.request())[0]["status"] == 204


@pytest.mark.parametrize("declared", [None, 1, MAP_VIEW_MAX_BODY_BYTES + 1])
async def test_excess_body_rejected_without_truncating_and_capacity_recovers(harness, declared):
    chunks = iter((b"x" * MAP_VIEW_MAX_BODY_BYTES, b"x"))

    async def receive():
        return {"type": "http.request", "body": next(chunks), "more_body": True}

    result = await harness.request(receive=receive, declared=declared)
    assert result[0]["status"] == 413
    assert harness.bodies == []
    assert (await harness.request())[0]["status"] == 204


async def test_exact_byte_limit_and_empty_chunks_replay_complete_bytes_once(harness):
    chunks = iter([(b"", True)] * 1000 + [(b"x" * MAP_VIEW_MAX_BODY_BYTES, True), (b"", False)])

    async def receive():
        chunk, more_body = next(chunks)
        return {"type": "http.request", "body": chunk, "more_body": more_body}

    result = await harness.request(receive=receive)
    assert result[0]["status"] == 204
    assert harness.bodies == [b"x" * MAP_VIEW_MAX_BODY_BYTES]


async def test_downstream_failure_releases_slot_without_replacing_started_response(harness):
    harness.fail_after_start = True
    with pytest.raises(InvalidRequest, match="Downstream failed"):
        await harness.request()
    harness.fail_after_start = False
    assert (await harness.request())[0]["status"] == 204


async def test_alternate_uuid_cannot_widen_the_map_cap_with_larger_ordinary_limit(harness):
    harness.app = BodySizeLimitMiddleware(harness.downstream, max_bytes=10 * 1024 * 1024)
    result = await harness.request(
        receive=forbidden_read, route=SAVE_PATHS[2], declared=MAP_VIEW_MAX_BODY_BYTES + 1
    )
    assert result[0]["status"] == 413
    assert (await harness.request(route=SAVE_PATHS[2]))[0]["status"] == 204


async def test_noncanonical_uuid_keeps_ordinary_byte_limit(harness):
    async def receive():
        return {"type": "http.request", "body": b"x" * 65537, "more_body": False}

    assert (await harness.request(receive=receive, route=SAVE_PATHS[2]))[0]["status"] == 413


async def test_immediately_available_empty_chunks_cannot_escape_deadline(harness, monkeypatch):
    monkeypatch.setattr(map_body_admission, "MAP_BODY_READ_TIMEOUT_SECONDS", 0.005)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": True}

    assert (await harness.request(receive=receive))[0]["status"] == 422
    assert (await harness.request())[0]["status"] == 204
