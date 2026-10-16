"""Separate cleanup/acquisition connections preserve current state at commit boundaries."""

import asyncio
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.sql.dml import Delete

from ase.adapters.persistence.dormant_retention import prune_push_receipts
from ase.adapters.persistence.selected_index_models import (
    SelectedIndexLossRow,
    SelectedIndexRecordRow,
)
from ase.adapters.persistence.selected_subscription_index import (
    SqlSelectedSubscriptionIndexRepository,
)
from ase.adapters.persistence.users import SqlUserRepository
from ase.adapters.persistence.web_push_models import PushDeliveryRow, PushDeviceRow
from ase.container.dormant_retention import DormantRetention
from dormant_retention_helpers import seed, selected_row, selected_scope
from helpers import USER_EMAIL, USER_PASSWORD, create_user
from test_selected_subscription_index import _record
from token_race_helpers import race_container as race_container  # noqa: PLC0414


async def test_selected_expiry_and_new_page_use_distinct_connections_and_shared_guard(
    race_container, monkeypatch
):
    container = race_container
    user = await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    scope = await selected_scope(container, user)
    now = container.clock.now()
    await seed(container, *[selected_row(scope, user.id, i, now) for i in range(1, 106)])
    locked, waiting, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
    connections = {}
    original = SqlUserRepository.lock_administration

    async def guarded(repository):
        name = asyncio.current_task().get_name()
        connection = await repository._session.connection()
        connections[name] = id(connection.sync_connection.connection.dbapi_connection)
        if name == "new-page":
            waiting.set()
        await original(repository)
        if name == "expiry":
            locked.set()
            await asyncio.wait_for(release.wait(), 10)

    monkeypatch.setattr(SqlUserRepository, "lock_administration", guarded)

    async def acquire():
        async with container.session_factory() as session:
            await SqlUserRepository(session).lock_administration()
            await SqlUserRepository(session).lock_by_id(user.id)
            await SqlSelectedSubscriptionIndexRepository(session).persist_page(
                scope,
                "usgs",
                actor_id=user.id,
                expected_revision=0,
                page_key="new",
                records=(_record("new"),),
                cursor_value="resume",
                watermark_at=None,
                now=now,
            )
            await session.commit()

    first = asyncio.create_task(DormantRetention(container).selected(), name="expiry")
    second = None
    try:
        await asyncio.wait_for(locked.wait(), 10)
        second = asyncio.create_task(acquire(), name="new-page")
        await asyncio.wait_for(waiting.wait(), 10)
        release.set()
        await asyncio.wait_for(asyncio.gather(first, second), 20)
        assert len(set(connections.values())) == 2
        async with container.session_factory() as session:
            records = list(await session.scalars(select(SelectedIndexRecordRow)))
            assert [row.item_key for row in records] == ["new"]
            assert (await session.scalar(select(SelectedIndexLossRow))).lost_items == 105
    finally:
        release.set()
        tasks = [first, *([second] if second is not None else [])]
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def test_push_claim_between_selection_and_deletion_preserves_fresh_lease(
    race_container, monkeypatch
):
    container = race_container
    user = await create_user(container, email=USER_EMAIL, password=USER_PASSWORD)
    now = container.clock.now()
    device = PushDeviceRow(
        id=uuid4(),
        user_id=user.id,
        family_id=uuid4(),
        security_version=0,
        endpoint_hash="b" * 64,
        encrypted_subscription="synthetic",
        created_at=now,
        next_check_at=now,
    )
    await seed(container, device)
    receipt = PushDeliveryRow(
        id=uuid4(),
        device_id=device.id,
        alert_id=uuid4(),
        state="pending",
        created_at=now - timedelta(days=8),
        updated_at=now - timedelta(days=8),
    )
    await seed(container, receipt)
    lease = uuid4()
    async with container.session_factory() as session:
        original = session.execute
        first_connection = await session.connection()

        async def interleave(statement, *args, **kwargs):
            if isinstance(statement, Delete):
                async with container.session_factory() as other:
                    second_connection = await other.connection()
                    assert (
                        first_connection.sync_connection.connection.dbapi_connection
                        is not second_connection.sync_connection.connection.dbapi_connection
                    )
                    await other.execute(
                        update(PushDeliveryRow)
                        .where(PushDeliveryRow.id == receipt.id)
                        .values(state="sending", lease_token=lease, updated_at=now)
                    )
                    await other.commit()
            return await original(statement, *args, **kwargs)

        monkeypatch.setattr(session, "execute", interleave)
        assert await prune_push_receipts(session, now) == 0
        await session.commit()
    async with container.session_factory() as session:
        kept = await session.get(PushDeliveryRow, receipt.id)
        assert (kept.state, kept.lease_token, kept.updated_at) == ("sending", lease, now)
