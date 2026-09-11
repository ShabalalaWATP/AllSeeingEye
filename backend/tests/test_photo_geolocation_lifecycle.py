"""Cancellation, usage accounting and explicit transient-receipt cleanup."""

import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ase.application.research.photo_model import PhotoVision
from ase.container import Container
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.llm import LlmMessage, LlmProfile, LlmRequest, LlmRole
from ase.domain.users import User
from helpers import USER_EMAIL, USER_PASSWORD, FakeClock, bearer, login_token
from photo_helpers import Vision, session_check, upload
from research_input_helpers import NOW, Harness, extracted


class Cipher:
    def decrypt(self, value: str) -> str:
        return value


def model() -> LlmProfile:
    return LlmProfile(
        uuid4(),
        "Fixture",
        "https://fixture.invalid/v1",
        "vision",
        "test-key",
        "key",
        frozenset({LlmRole.ASSESSMENT}),
        4000,
        0.1,
        True,
        NOW,
        NOW,
    )


@pytest.mark.parametrize("failure", ["timeout", "oversized", "unexpected", "cancel"])
async def test_incomplete_vision_accounts_safely_and_cancels(failure: str) -> None:
    gateway = Vision()
    usage = []

    async def record(item) -> None:
        usage.append(item)

    service = PhotoVision(gateway, Cipher(), FakeClock(NOW), record)
    if failure == "timeout":
        gateway.error = TimeoutError()
    elif failure == "oversized":
        gateway.content = "s" * 32_001
    elif failure == "unexpected":
        gateway.error = RuntimeError("sensitive provider implementation detail")
    else:

        async def wait() -> None:
            await asyncio.Event().wait()

        gateway.after = wait
    request = LlmRequest((LlmMessage("user", "Where?"),), 4000, 0.1)
    task = asyncio.create_task(service.analyse(uuid4(), model(), request, session_check))
    if failure == "cancel":
        await gateway.started.wait()
        task.cancel()
    expected = {
        "timeout": InvalidRequest,
        "oversized": InvalidRequest,
        "unexpected": RuntimeError,
        "cancel": asyncio.CancelledError,
    }[failure]
    with pytest.raises(expected):
        await task
    assert len(usage) == 1 and not usage[0].ok
    assert "sensitive" not in str(usage[0])


async def test_discard_child_preserves_original_and_frees_a_retry_slot() -> None:
    harness = Harness()
    receipt = await harness.service.execute(harness.actor, "notes.txt", b"Original text")
    reservation = harness.store.reserve(harness.actor, "notes.txt")
    derived = harness.store.put(reservation, replace(extracted(), parent_input_id=receipt.id))
    harness.store.discard(harness.actor, derived.receipt.id)
    assert harness.store.read(harness.actor, receipt.id)
    retry = harness.store.reserve(harness.actor, "notes.txt")
    harness.store.release(retry)
    with pytest.raises(NotFound):
        harness.store.read(harness.actor, derived.receipt.id)


async def test_discard_parent_removes_children_without_touching_foreign_receipts() -> None:
    harness = Harness()
    receipt = await harness.service.execute(harness.actor, "notes.txt", b"Original text")
    reservation = harness.store.reserve(harness.actor, "notes.txt")
    harness.store.put(reservation, replace(extracted(), parent_input_id=receipt.id))
    other = replace(harness.actor, id=uuid4())
    unrelated = harness.store.reserve(other, "notes.txt")
    foreign = harness.store.put(unrelated, extracted())
    with pytest.raises(NotFound):
        harness.store.discard(other, receipt.id)
    await harness.service.discard(harness.actor, receipt.id, before_discard=session_check)
    assert list(harness.store._ready) == [foreign.receipt.id]
    assert not harness.identity.locked


async def test_http_discard_requires_owner_and_returns_no_cache(
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    receipt_id = upload(container, user)
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    response = await client.delete(f"/api/research/inputs/{receipt_id}", headers=bearer(token))
    assert response.status_code == 204 and response.content == b""
    assert response.headers["cache-control"] == "private, no-store"
    assert (
        await client.delete(f"/api/research/inputs/{receipt_id}", headers=bearer(token))
    ).status_code == 404
