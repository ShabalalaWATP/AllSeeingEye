"""A stale delivery reader must observe pruning after acquiring the shared guard."""

import asyncio
from datetime import timedelta

import pytest

from alert_routing_helpers import delivery_store, enable_mail, fire, outbox, rule, save_route
from ase.adapters.persistence.users import SqlUserRepository
from ase.adapters.persistence.warning_store import SqlWarningStore
from ase.domain.notification_delivery import DeliveryOutcome


@pytest.fixture
def settings(settings, tmp_path):
    if settings.database_url.startswith("sqlite"):
        # The ordinary in-memory StaticPool cannot demonstrate independent transactions.
        return settings.model_copy(
            update={"database_url": f"sqlite+aiosqlite:///{tmp_path / 'alert-prune.sqlite'}"}
        )
    return settings


async def test_preparation_refreshes_after_prune_on_another_connection(
    client, container, user, monkeypatch
):
    headers, identifier = await rule(client, user)
    await enable_mail(container, user)
    await save_route(client, headers, identifier)
    await fire(container, identifier)
    delivery = delivery_store(container)
    claim = await delivery.claim(container.clock.now())
    assert claim is not None
    container.clock.advance(timedelta(days=31))
    reached, resume = asyncio.Event(), asyncio.Event()
    connections = {}
    original = SqlUserRepository.lock_administration

    async def lock(repository):
        task = asyncio.current_task()
        name = task.get_name() if task else ""
        if name in {"retention-prepare", "retention-prune"}:
            connection = await repository._session.connection()
            connections[name] = id(connection.sync_connection.connection.dbapi_connection)
        if name == "retention-prepare" and not reached.is_set():
            reached.set()
            await asyncio.wait_for(resume.wait(), 10)
        await original(repository)

    monkeypatch.setattr(SqlUserRepository, "lock_administration", lock)
    preparation = asyncio.create_task(
        delivery.prepare(claim, container.clock.now()), name="retention-prepare"
    )
    pruning = None
    try:
        await asyncio.wait_for(reached.wait(), 10)
        store = SqlWarningStore(container.session_factory, container.access_policy)
        pruning = asyncio.create_task(
            store.prune(container.clock.now() - timedelta(days=30)), name="retention-prune"
        )
        assert await asyncio.wait_for(pruning, 10) == 1
        assert len(set(connections.values())) == 2
        resume.set()
        assert await asyncio.wait_for(preparation, 10) is None
        await delivery.finish(claim, DeliveryOutcome.SENT, container.clock.now())
        assert await outbox(container) == []
    finally:
        resume.set()
        tasks = [preparation, *([pruning] if pruning is not None else [])]
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
