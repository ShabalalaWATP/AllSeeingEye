"""Activation cannot commit inside the final source-admission/release critical section."""

import asyncio
from contextlib import asynccontextmanager

import pytest
from httpx import AsyncClient

from ase.application.dto import RequestContext
from ase.application.research.source_admission import ControlledResearchProvider
from ase.container import Container
from ase.domain.research import ResearchBatch
from ase.domain.users import User
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, login_token
from test_events_api import app  # noqa: F401
from test_research_collection import QUERY, Provider, event


@pytest.mark.parametrize("private", [False, True])
@pytest.mark.parametrize("cancelled", [False, True])
async def test_disable_waits_for_release_after_final_enabled_read(
    client: AsyncClient,
    container: Container,
    admin: User,
    monkeypatch: pytest.MonkeyPatch,
    private: bool,
    cancelled: bool,
) -> None:
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    claims = container.issuer.verify(token)
    gate = container.source_admission
    original_enabled, original_guard = gate.enabled, gate.guard
    final_read = asyncio.Event()
    release = asyncio.Event()
    disable_waiting = asyncio.Event()
    checks = 0
    guards = 0
    order: list[str] = []

    async def enabled(source_id: str) -> bool:
        nonlocal checks
        result = await original_enabled(source_id)
        checks += 1
        if checks == 2:
            # Model an asynchronous database-session close after the final SELECT.
            final_read.set()
            await release.wait()
        return result

    @asynccontextmanager
    async def guard():
        nonlocal guards
        guards += 1
        if guards == 2:
            disable_waiting.set()
        async with original_guard():
            yield

    monkeypatch.setattr(gate, "enabled", enabled)
    monkeypatch.setattr(gate, "guard", guard)

    async def collect() -> None:
        if private:
            provider = Provider("fake_feed", ResearchBatch(items=(event("private"),)))
            result = await ControlledResearchProvider(provider, gate).collect(QUERY)
            assert result.items
        else:
            result = await container.scheduler.poll_once(container.connectors[0])
            assert result.ok
        order.append("released")

    async def deactivate() -> None:
        async with container.session_factory() as session:
            await container.admin_source_controls(session).activate(
                claims,
                "fake_feed",
                False,
                RequestContext(),
            )
        order.append("disabled")

    collection = asyncio.create_task(collect())
    await asyncio.wait_for(final_read.wait(), 2)
    activation = asyncio.create_task(deactivate())
    await asyncio.wait_for(disable_waiting.wait(), 2)
    assert not activation.done()
    if cancelled:
        collection.cancel()
        with pytest.raises(asyncio.CancelledError):
            await collection
        await asyncio.wait_for(activation, 2)
        assert order == ["disabled"]
        assert container.store.stats().total == 0
    else:
        release.set()
        await asyncio.wait_for(asyncio.gather(collection, activation), 2)
        assert order == ["released", "disabled"]
    assert not await original_enabled("fake_feed")
