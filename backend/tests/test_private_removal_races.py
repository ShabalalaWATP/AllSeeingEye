"""Independent connections fence delayed writers and outbox claims around removal."""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from ase.adapters.persistence.assistant_history_models import AssistantConversationRow
from ase.adapters.persistence.models import ReportRow
from ase.adapters.persistence.subscription_edition_models import SubscriptionDeliveryRow
from ase.adapters.persistence.users import SqlUserRepository
from ase.domain.errors import Conflict, NotFound
from ase.domain.private_removal import RemovalRequest, RemovalScope
from ase.domain.users import Role
from helpers import create_user
from private_removal_helpers import apply, authorise, preview, report, subscription
from token_race_helpers import race_container as race_container  # noqa: PLC0414


async def test_delayed_report_conversation_cannot_recreate_removed_reference(
    race_container, monkeypatch
):
    container = race_container
    owner = await create_user(container, email="owner@example.com", password=None)
    admin = await create_user(
        container, email="operator@example.com", password=None, role=Role.ADMIN
    )
    await authorise(container, admin, owner)
    target, _ = await report(container, owner)
    request = RemovalRequest(owner.id, RemovalScope.REPORT, target.id)
    plan = await preview(container, admin, request)
    locked, waiting, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    connections = {}
    original = SqlUserRepository.lock_administration

    async def guarded(repository):
        name = asyncio.current_task().get_name()
        connection = await repository._session.connection()
        connections[name] = id(connection.sync_connection.connection.dbapi_connection)
        if name == "late-save":
            waiting.set()
        await original(repository)
        if name == "remove":
            locked.set()
            await asyncio.wait_for(release.wait(), 10)

    monkeypatch.setattr(SqlUserRepository, "lock_administration", guarded)

    async def save():
        async with container.session_factory() as session:
            service = container.assistant_history(session)
            with pytest.raises(NotFound):
                await service.save(owner, "Late transcript", [{"answer": {}}], [(target.id, 1)])
            await session.rollback()

    first = asyncio.create_task(apply(container, admin, request, plan.fingerprint), name="remove")
    second = None
    try:
        await asyncio.wait_for(locked.wait(), 10)
        second = asyncio.create_task(save(), name="late-save")
        await asyncio.wait_for(waiting.wait(), 10)
        release.set()
        await asyncio.wait_for(asyncio.gather(first, second), 20)
        assert len(set(connections.values())) == 2
        async with container.session_factory() as session:
            assert await session.get(ReportRow, target.id) is None
            assert await session.scalar(select(AssistantConversationRow)) is None
    finally:
        release.set()
        tasks = [first, *([second] if second else [])]
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def test_delivery_claim_winning_before_apply_is_preserved(race_container, monkeypatch):
    container = race_container
    owner = await create_user(container, email="owner@example.com", password=None)
    admin = await create_user(
        container, email="operator@example.com", password=None, role=Role.ADMIN
    )
    await authorise(container, admin, owner)
    schedule, edition = await subscription(container, owner)
    now = container.clock.now()
    delivery_id = uuid4()
    async with container.session_factory() as session:
        session.add(
            SubscriptionDeliveryRow(
                id=delivery_id,
                edition_id=edition.id,
                channel="email",
                destination_ref=owner.id,
                event_kind="edition_ready",
                idempotency_key=uuid4(),
                state="pending",
                attempts=0,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()
    request = RemovalRequest(owner.id, RemovalScope.SUBSCRIPTION, schedule.id)
    plan = await preview(container, admin, request)
    claimed, waiting, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    connections = {}
    original = SqlUserRepository.lock_administration

    async def guard(repository):
        connection = await repository._session.connection()
        connections["remove"] = id(connection.sync_connection.connection.dbapi_connection)
        waiting.set()
        await original(repository)

    monkeypatch.setattr(SqlUserRepository, "lock_administration", guard)

    async def claim():
        async with container.session_factory() as session:
            connection = await session.connection()
            connections["claim"] = id(connection.sync_connection.connection.dbapi_connection)
            await session.execute(
                update(SubscriptionDeliveryRow)
                .where(SubscriptionDeliveryRow.id == delivery_id)
                .values(state="sending", attempts=1, lease_token=uuid4())
            )
            claimed.set()
            await asyncio.wait_for(release.wait(), 10)
            await session.commit()

    first = asyncio.create_task(claim())
    second = None
    try:
        await asyncio.wait_for(claimed.wait(), 10)
        second = asyncio.create_task(apply(container, admin, request, plan.fingerprint))
        await asyncio.wait_for(waiting.wait(), 10)
        release.set()
        await first
        with pytest.raises(Conflict, match="active_or_uncertain_delivery"):
            await asyncio.wait_for(second, 20)
        assert len(set(connections.values())) == 2
        async with container.session_factory() as session:
            assert (await session.get(SubscriptionDeliveryRow, delivery_id)).state == "sending"
    finally:
        release.set()
        tasks = [first, *([second] if second else [])]
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
