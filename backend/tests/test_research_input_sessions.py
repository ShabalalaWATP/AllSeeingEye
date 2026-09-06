"""A private upload may complete only under its original live access session."""

import asyncio
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from ase.adapters.research_inputs.memory import BoundedResearchInputStore
from ase.application.ports.research_inputs import InputExtraction
from ase.container import Container
from ase.domain.errors import NotFound, Unauthenticated
from ase.domain.users import User
from helpers import CSRF_COOKIE, USER_EMAIL, USER_PASSWORD, FakeClock, bearer, login_token
from research_input_helpers import Harness, extracted


class ControlledExtraction:
    def __init__(self) -> None:
        self.started, self.finish = asyncio.Event(), asyncio.Event()
        self.cleaned = False

    async def extract(self, data: bytes, filename: str, captured_at: datetime) -> InputExtraction:
        self.started.set()
        try:
            await self.finish.wait()
            return extracted(filename, data)
        finally:
            self.cleaned = True


@pytest.mark.parametrize(
    "transition",
    [
        "logout",
        "expiry",
        "logout_then_login",
        "refresh_then_expiry",
        "live",
        "refresh",
        "logout_other_session",
    ],
)
async def test_upload_rechecks_original_session_after_extraction(
    transition: str, client: AsyncClient, container: Container, user: User, clock: FakeClock
) -> None:
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    if transition.endswith("expiry"):
        remaining = container.issuer.verify(token).expires_at - clock.now()
        clock.advance(remaining - timedelta(seconds=10))
    extractor = ControlledExtraction()
    container.research_importer = extractor
    store = container.research_inputs
    assert isinstance(store, BoundedResearchInputStore)
    upload = asyncio.create_task(
        client.post(
            "/api/research/inputs?filename=private.txt",
            content=b"Private synthetic upload.",
            headers={**bearer(token), "Content-Type": "application/octet-stream"},
        )
    )
    try:
        await asyncio.wait_for(extractor.started.wait(), timeout=5)
        pending_id = next(iter(store._reservations))
        if transition == "logout_other_session":
            await login_token(client, USER_EMAIL, USER_PASSWORD)
        if transition.startswith("logout"):
            response = await client.post(
                "/api/auth/logout", headers={"X-CSRF-Token": client.cookies[CSRF_COOKIE]}
            )
            assert response.status_code == 204
            if transition == "logout_then_login":
                await login_token(client, USER_EMAIL, USER_PASSWORD)
        elif transition.startswith("refresh"):
            response = await client.post(
                "/api/auth/refresh", headers={"X-CSRF-Token": client.cookies[CSRF_COOKIE]}
            )
            assert response.status_code == 200
        if transition.endswith("expiry"):
            clock.advance(timedelta(seconds=11))
        extractor.finish.set()
        response = await upload
    finally:
        if not upload.done():
            upload.cancel()
        await asyncio.gather(upload, return_exceptions=True)
    assert extractor.cleaned
    if transition in {"live", "refresh", "logout_other_session"}:
        assert response.status_code == 201
        assert store.read(user, pending_id).receipt.preview == "Private synthetic upload."
    else:
        assert response.status_code == 401
        with pytest.raises(NotFound):
            store.read(user, pending_id)
        assert not store._reservations and not store._ready


@pytest.mark.parametrize("error", [Unauthenticated(), asyncio.CancelledError()])
async def test_before_retain_failure_releases_guard_and_pending_slot(error: BaseException) -> None:
    harness = Harness()

    async def reject() -> None:
        assert harness.identity.locked
        assert harness.extractor.calls == 1
        assert not harness.store._ready
        raise error

    with pytest.raises(type(error)):
        await harness.service.execute(
            harness.actor, "private.txt", b"Private fixture.", before_retain=reject
        )
    assert not harness.identity.locked and not harness.store._reservations
    assert not harness.store._ready


async def test_before_retain_runs_after_account_guard_before_synchronous_put() -> None:
    harness = Harness()
    checked = False

    async def check() -> None:
        nonlocal checked
        assert harness.identity.locked and harness.extractor.calls == 1
        assert not harness.store._ready
        checked = True

    receipt = await harness.service.execute(
        harness.actor, "private.txt", b"Private fixture.", before_retain=check
    )
    assert checked and harness.store.read(harness.actor, receipt.id)
