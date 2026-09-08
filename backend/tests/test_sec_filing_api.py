"""Real authentication, private retention and original download around SEC transport."""

import asyncio
from datetime import timedelta
from uuid import UUID

import httpx
import pytest
from httpx import AsyncClient

from ase.adapters.research_inputs.memory import BoundedResearchInputStore
from ase.container import Container
from ase.domain.users import User
from helpers import CSRF_COOKIE, USER_EMAIL, USER_PASSWORD, FakeClock, bearer, login_token
from sec_filings_helpers import CONTENT, DOCUMENT, INDEX, SecTransport

SEARCH = {"cik": "1234", "since": "2026-01-01", "until": "2026-09-01"}
BASE = "/api/research/sec/filings"


async def selected(client: AsyncClient, token: str) -> str:
    response = await client.post(BASE, json=SEARCH, headers=bearer(token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["items"][0]["filing_date"] == "2026-08-31"
    return str(body["items"][0]["selection_id"])


async def test_filing_import_enters_existing_private_research_input_and_inert_original(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    transport = SecTransport(monkeypatch)
    container.sec_client = transport.client
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    try:
        key = await selected(client, token)
        assert (
            await client.get(f"{BASE}/{key}/original", headers=bearer(token))
        ).status_code == 404
        response = await client.post(f"{BASE}/{key}/import", headers=bearer(token))
        assert response.status_code == 201, response.text
        receipt = response.json()
        stored = container.research_inputs.read(user, UUID(receipt["id"]))
        assert stored.events[0].summary == "The issuer reported revenue of GBP 12 million."
        assert stored.events[0].attributes["original_sha256"] == receipt["sha256"]
        original = await client.get(f"{BASE}/{key}/original", headers=bearer(token))
        assert original.content == CONTENT
        assert original.headers["content-type"] == "application/octet-stream"
        assert original.headers["content-disposition"] == 'attachment; filename="filing.htm"'
        assert original.headers["cache-control"] == "private, no-store"
        assert original.headers["x-content-type-options"] == "nosniff"
        # Reimport rejection must never destroy the retained original.
        assert (await client.post(f"{BASE}/{key}/import", headers=bearer(token))).status_code == 429
        assert (
            await client.get(f"{BASE}/{key}/original", headers=bearer(token))
        ).content == CONTENT
        assert len(transport.requests) == 2
    finally:
        await transport.http.aclose()


@pytest.mark.parametrize("transition", ["logout", "logout_login", "expiry", "live"])
async def test_private_retention_rechecks_original_refresh_family_after_download(
    transition: str,
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
    container: Container,
    user: User,
    clock: FakeClock,
) -> None:
    transport = SecTransport(monkeypatch)
    container.sec_client = transport.client
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    started, finish = asyncio.Event(), asyncio.Event()

    async def hold(request: httpx.Request) -> None:
        if str(request.url) == DOCUMENT:
            started.set()
            await finish.wait()

    transport.before = hold
    job = None
    try:
        key = await selected(client, token)
        job = asyncio.create_task(client.post(f"{BASE}/{key}/import", headers=bearer(token)))
        await asyncio.wait_for(started.wait(), 5)
        if transition.startswith("logout"):
            assert (
                await client.post(
                    "/api/auth/logout",
                    headers={
                        "X-CSRF-Token": client.cookies[CSRF_COOKIE],
                    },
                )
            ).status_code == 204
            if transition == "logout_login":
                await login_token(client, USER_EMAIL, USER_PASSWORD)
        elif transition == "expiry":
            clock.advance(
                container.issuer.verify(token).expires_at - clock.now() + timedelta(seconds=1)
            )
        finish.set()
        response = await job
        store = container.research_inputs
        assert isinstance(store, BoundedResearchInputStore)
        if transition == "live":
            assert response.status_code == 201, response.text
            assert len(store._ready) == 1
        else:
            assert not store._reservations
            assert response.status_code == 401, response.text
            assert not store._ready
            assert not any(
                item.original or item.reserved for item in container.sec_selections._items.values()
            )
    finally:
        if job is not None and not job.done():
            job.cancel()
            await asyncio.gather(job, return_exceptions=True)
        await transport.http.aclose()


async def test_pending_capacity_precedes_fetch_and_session_choices_are_private(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    transport = SecTransport(monkeypatch)
    container.sec_client = transport.client
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    reservations = []
    try:
        key = await selected(client, token)
        for filename in ("one.txt", "two.txt"):
            reservations.append(container.research_inputs.reserve(user, filename))
        response = await client.post(f"{BASE}/{key}/import", headers=bearer(token))
        assert response.status_code == 429
        assert [str(request.url) for request in transport.requests] == [INDEX]
        assert not any(item.reserved for item in container.sec_selections._items.values())
        other = await login_token(client, USER_EMAIL, USER_PASSWORD)
        assert (await client.post(f"{BASE}/{key}/import", headers=bearer(other))).status_code == 404
        assert (
            await client.get(f"{BASE}/{key}/original", headers=bearer(other))
        ).status_code == 404
    finally:
        for reservation in reservations:
            container.research_inputs.release(reservation)
        await transport.http.aclose()


async def test_cancelled_fetch_releases_both_reservations(
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncClient,
    container: Container,
    user: User,
) -> None:
    transport = SecTransport(monkeypatch)
    container.sec_client = transport.client
    token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    started = asyncio.Event()

    async def hold(request: httpx.Request) -> None:
        if str(request.url) == DOCUMENT:
            started.set()
            await asyncio.Event().wait()

    transport.before = hold
    try:
        key = await selected(client, token)
        async with container.session_factory() as session:
            task = asyncio.create_task(
                container.sec_filings(session).import_filing(
                    container.issuer.verify(token),
                    UUID(key),
                )
            )
            await asyncio.wait_for(started.wait(), 5)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        store = container.research_inputs
        assert isinstance(store, BoundedResearchInputStore)
        assert not store._ready and not store._reservations
        assert not any(item.reserved for item in container.sec_selections._items.values())
    finally:
        await transport.http.aclose()
