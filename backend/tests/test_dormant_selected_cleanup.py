"""Bounded independent expiry preserves corrections, losses and acquisition cursors."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from ase.adapters.persistence.selected_index_expiry import expire_selected_metadata
from ase.adapters.persistence.selected_index_models import (
    SelectedIndexCursorRow,
    SelectedIndexGateRow,
    SelectedIndexLossRow,
    SelectedIndexRecordRow,
)
from ase.adapters.persistence.selected_subscription_index import (
    SqlSelectedSubscriptionIndexRepository,
)
from ase.container.dormant_retention import DormantRetention
from ase.domain.errors import Conflict
from dormant_retention_helpers import seed, selected_row, selected_scope


async def test_expiry_filters_before_read_limit_and_preserves_exact_live_boundary(container, user):
    now = container.clock.now()
    scope = await selected_scope(container, user)
    await seed(
        container,
        selected_row(scope, user.id, 1, now, expires_at=now + timedelta(microseconds=1)),
        selected_row(scope, user.id, 2, now),
        selected_row(
            scope,
            user.id,
            3,
            now,
            first_seen_at=now - timedelta(days=400),
            expires_at=now + timedelta(days=1),
        ),
    )
    async with container.session_factory() as session:
        records = await SqlSelectedSubscriptionIndexRepository(session).list_records(
            scope, actor_id=user.id, now=now, limit=1
        )
        assert [row.id for row in records] == [1]
        assert await expire_selected_metadata(session, now) == (None, None, 2)
        await session.commit()
    async with container.session_factory() as session:
        assert list(await session.scalars(select(SelectedIndexRecordRow.id))) == [1]
        assert (await session.scalar(select(SelectedIndexLossRow))).lost_items == 2


async def test_backlog_rotates_past_live_rows_and_coalesces_loss_without_cursor_rewrite(
    container, user
):
    now = container.clock.now()
    scope = await selected_scope(container, user)
    await seed(
        container,
        *[
            selected_row(
                scope,
                user.id,
                index,
                now,
                expires_at=now + timedelta(days=1) if index <= 100 else now,
            )
            for index in range(1, 306)
        ],
        SelectedIndexCursorRow(
            subscription_id=scope,
            source_id="usgs",
            owner_id=user.id,
            revision=7,
            cursor_value="resume",
            last_page_key="last",
            last_page_sha256="a" * 64,
            updated_at=now,
        ),
    )
    maintenance = DormantRetention(container)
    for position, count in [(100, 305), (200, 205), (300, 105), (None, 100)]:
        await maintenance.selected()
        assert maintenance.selected_after == position
        async with container.session_factory() as session:
            assert (
                await session.scalar(select(func.count()).select_from(SelectedIndexRecordRow))
                == count
            )
    async with container.session_factory() as session:
        loss = await session.scalar(select(SelectedIndexLossRow))
        assert loss.reason == "age" and loss.lost_items == 205
        cursor = await session.get(SelectedIndexCursorRow, (scope, "usgs"))
        assert (cursor.revision, cursor.cursor_value, cursor.last_page_key) == (7, "resume", "last")


async def test_correction_fanout_is_drained_in_batches_without_losing_fingerprints(container, user):
    now = container.clock.now()
    scope = await selected_scope(container, user)
    await seed(container, selected_row(scope, user.id, 1, now))
    fingerprint = f"{1:064x}"
    await seed(
        container,
        *[
            selected_row(
                scope,
                user.id,
                index,
                now,
                corrects_id=1,
                corrects_fingerprint=fingerprint,
                expires_at=now + timedelta(days=1),
            )
            for index in range(2, 207)
        ],
    )
    maintenance = DormantRetention(container)
    for cycle in range(7):
        await maintenance.selected()
        async with container.session_factory() as session:
            assert (await session.get(SelectedIndexRecordRow, 1) is None) == (cycle == 6)
    async with container.session_factory() as session:
        rows = list(await session.scalars(select(SelectedIndexRecordRow)))
        assert len(rows) == 205
        assert all(
            row.corrects_id is None and row.corrects_fingerprint == fingerprint for row in rows
        )
        assert (await session.scalar(select(SelectedIndexLossRow))).lost_items == 1


async def test_failed_transaction_restores_data_links_loss_and_scan_cursor(
    container, user, monkeypatch
):
    now = container.clock.now()
    scope = await selected_scope(container, user)
    await seed(container, selected_row(scope, user.id, 1, now))
    await seed(
        container,
        selected_row(
            scope,
            user.id,
            2,
            now,
            corrects_id=1,
            corrects_fingerprint=f"{1:064x}",
            expires_at=now + timedelta(days=1),
        ),
    )
    original = expire_selected_metadata

    async def fail(session, *args, **kwargs):
        await original(session, *args, **kwargs)
        raise RuntimeError("failed transaction")

    monkeypatch.setattr("ase.container.dormant_retention.expire_selected_metadata", fail)
    maintenance = DormantRetention(container)
    with pytest.raises(RuntimeError):
        await maintenance.selected()
    assert maintenance.selected_after is None
    async with container.session_factory() as session:
        assert await session.get(SelectedIndexRecordRow, 1) is not None
        assert (await session.get(SelectedIndexRecordRow, 2)).corrects_id == 1
        assert await session.scalar(select(SelectedIndexLossRow)) is None
        assert (await session.get(SelectedIndexGateRow, 1)).revision == 0


async def test_missing_write_gate_fails_closed(container):
    async with container.session_factory() as session:
        with pytest.raises(Conflict):
            await expire_selected_metadata(session, container.clock.now())


async def test_empty_index_and_reused_low_id_start_a_fresh_rotation(container, user):
    scope = await selected_scope(container, user)
    maintenance = DormantRetention(container)
    await maintenance.selected()
    assert (maintenance.selected_after, maintenance.selected_through) == (None, None)
    for _ in range(2):
        await seed(container, selected_row(scope, user.id, 1, container.clock.now()))
        await maintenance.selected()
    async with container.session_factory() as session:
        assert await session.get(SelectedIndexRecordRow, 1) is None
        assert (await session.scalar(select(SelectedIndexLossRow))).lost_items == 2


async def test_continuing_acquisition_cannot_starve_earlier_expiry(container, user, clock):
    now = clock.now()
    scope = await selected_scope(container, user)
    await seed(
        container,
        *[
            selected_row(scope, user.id, index, now, expires_at=now + timedelta(seconds=1))
            for index in range(1, 201)
        ],
    )
    maintenance = DormantRetention(container)
    await maintenance.selected()
    assert (maintenance.selected_after, maintenance.selected_through) == (100, 200)
    clock.advance(timedelta(seconds=2))
    await seed(
        container,
        *[
            selected_row(scope, user.id, index, clock.now(), expires_at=now + timedelta(days=1))
            for index in range(201, 401)
        ],
    )
    await maintenance.selected()
    assert (maintenance.selected_after, maintenance.selected_through) == (None, None)
    await maintenance.selected()
    async with container.session_factory() as session:
        assert (
            await session.scalar(
                select(SelectedIndexRecordRow.id).where(SelectedIndexRecordRow.id <= 200)
            )
            is None
        )


@pytest.mark.parametrize("limit", [0, 101])
async def test_invalid_batch_is_rejected(container, limit):
    async with container.session_factory() as session:
        with pytest.raises(ValueError):
            await expire_selected_metadata(session, container.clock.now(), limit=limit)
