"""Asset reservations, inert byte retrieval and transactional lifecycle storage."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import event, select, update
from sqlalchemy.exc import IntegrityError

from ase.adapters.persistence.original_asset_models import OriginalAssetRow
from ase.adapters.persistence.original_assets import SqlOriginalAssetRepository
from ase.domain.original_assets import OriginalAsset
from report_documents_helpers import document_records
from test_report_team_scope import team_for


async def seed(container, user):
    report, version = document_records(user.id)
    now = container.clock.now()
    asset = OriginalAsset(
        uuid4(),
        report.id,
        version.id,
        version.number,
        "E1",
        "research_import",
        "private-event",
        "a" * 64,
        4,
        "original.pdf",
        "application/pdf",
        "Owned original",
        user.id,
        None,
        user.id,
        now,
        now + timedelta(days=30),
        now + timedelta(minutes=5),
    )
    asset = replace(asset, session_family_id=uuid4())
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(report, version)
        await SqlOriginalAssetRepository(session).create(asset)
        await session.commit()
    return asset


async def test_reservation_activation_is_conditional_and_metadata_avoids_bytes(container, user):
    asset = await seed(container, user)
    now = container.clock.now()
    async with container.session_factory() as session:
        repo = SqlOriginalAssetRepository(session)
        assert await repo.usage() == (1, 4)
        assert await repo.usage(user.id) == (1, 4)
        assert await repo.usage(uuid4()) == (0, 0)
        assert await repo.pending_count() == 1
        assert not await repo.activate(asset.id, b"data", now)
        assert await repo.begin_upload(asset.id, now)
        assert not await repo.begin_upload(asset.id, now)
        assert not await repo.activate(asset.id, b"bad", now)
        assert await repo.activate(asset.id, b"data", now)
        assert not await repo.activate(asset.id, b"evil", now)
        await session.commit()
    statements = []

    def capture(conn, cursor, statement, params, context, many):
        statements.append(statement)

    event.listen(container.engine.sync_engine, "before_cursor_execute", capture)
    try:
        async with container.session_factory() as session:
            repo = SqlOriginalAssetRepository(session)
            retained = await repo.get(asset.id)
            assert retained == replace(
                asset,
                status="active",
                transitioned_at=now,
                reservation_expires_at=now + timedelta(minutes=2),
            )
            assert await repo.list(asset.report_id, asset.version_number) == (retained,)
            assert await repo.list(asset.report_id, asset.version_number + 1) == ()
            assert all("original_assets.content" not in query for query in statements)
            content = await repo.content(asset.id)
            assert content.asset == retained and content.content == b"data"
            assert await repo.pending_count() == 0
    finally:
        event.remove(container.engine.sync_engine, "before_cursor_execute", capture)


@pytest.mark.parametrize("state", ["reserved", "uploading", "active"])
async def test_expiry_scrubs_bytes_and_private_metadata(container, user, state):
    asset = await seed(container, user)
    now = container.clock.now()
    async with container.session_factory() as session:
        repo = SqlOriginalAssetRepository(session)
        if state != "reserved":
            assert await repo.begin_upload(asset.id, now)
        if state == "active":
            assert await repo.activate(asset.id, b"data", now)
        expiry = (
            asset.expires_at
            if state == "active"
            else (await repo.get(asset.id)).reservation_expires_at
        )
        await repo.expire(expiry - timedelta(microseconds=1))
        assert (await repo.get(asset.id)).status == state
        await repo.expire(expiry)
        tombstone = await repo.get(asset.id)
        assert tombstone.status == "expired" and tombstone.transitioned_at == expiry
        assert tombstone.byte_count == 0
        assert not any(
            (
                tombstone.filename,
                tombstone.sha256,
                tombstone.evidence_label,
                tombstone.source_id,
                tombstone.event_id,
                tombstone.permitted_use,
            )
        )
        assert await repo.content(asset.id) is None
        assert await session.scalar(select(OriginalAssetRow.content)) is None
        assert await repo.usage() == (1, 0)
        assert await repo.list(asset.report_id, asset.version_number) == ()
        assert not await repo.begin_upload(asset.id, expiry)
        assert not await repo.activate(asset.id, b"data", expiry)


async def test_deletion_and_parent_cleanup_are_transactional(container, user):
    asset = await seed(container, user)
    now = container.clock.now()
    async with container.session_factory() as session:
        repo = SqlOriginalAssetRepository(session)
        await repo.begin_upload(asset.id, now)
        await repo.activate(asset.id, b"data", now)
        await session.commit()
        await repo.delete(asset.id, now)
        assert await repo.content(asset.id) is None
        await session.rollback()
        assert (await repo.content(asset.id)).content == b"data"
        await container.repositories(session).reports.delete(asset.report_id)
        assert await repo.get(asset.id) is None
        await session.rollback()
        assert (await repo.content(asset.id)).content == b"data"
        await repo.delete(asset.id, now)
        await repo.delete(asset.id, now + timedelta(days=1))
        assert (await repo.get(asset.id)).transitioned_at == now
        await session.commit()
        assert await repo.content(asset.id) is None
        await container.repositories(session).reports.delete(asset.report_id)
        await session.commit()
        assert await repo.get(asset.id) is None


async def test_rejects_wrong_version_anchor_and_nonreservation(container, user):
    asset = await seed(container, user)
    async with container.session_factory() as session:
        repo = SqlOriginalAssetRepository(session)
        with pytest.raises(ValueError, match="exact parent"):
            await repo.create(replace(asset, id=uuid4(), version_number=asset.version_number + 1))
        with pytest.raises(ValueError, match="reservation"):
            await repo.create(replace(asset, id=uuid4(), status="active"))


async def test_team_and_personal_usage_are_isolated_even_for_identical_hashes(
    container, user, admin
):
    asset = await seed(container, user)
    team = await team_for(container, admin, user)
    async with container.session_factory() as session:
        repo = SqlOriginalAssetRepository(session)
        await repo.create(replace(asset, id=uuid4(), team_id=team.id))
        assert await repo.usage() == (2, 8)
        assert await repo.usage(user.id) == (1, 4)
        assert await repo.usage(team_id=team.id) == (1, 4)
        assert await repo.usage(uuid4(), team.id) == (1, 4)
        assert await repo.usage(team_id=uuid4()) == (0, 0)


@pytest.mark.parametrize(
    "change",
    [
        {"status": "active"},
        {"status": "active", "content": b"too long"},
        {"status": "deleted"},
        {"content": b"data"},
        {"byte_count": 8388609},
        {"status": "unexpected"},
    ],
)
async def test_database_rejects_invalid_content_lifecycle(container, user, change):
    asset = await seed(container, user)
    async with container.session_factory() as session:
        with pytest.raises(IntegrityError):
            await session.execute(
                update(OriginalAssetRow).where(OriginalAssetRow.id == asset.id).values(**change)
            )
        await session.rollback()
        assert (await SqlOriginalAssetRepository(session).get(asset.id)).status == "reserved"


async def test_tombstones_count_towards_quota_until_exact_thirty_day_purge(container, user):
    asset = await seed(container, user)
    now = container.clock.now()
    async with container.session_factory() as session:
        repo = SqlOriginalAssetRepository(session)
        await repo.delete(asset.id, now)
        assert await repo.usage(user.id) == (1, 0)
        assert (await repo.get(asset.id)).session_family_id is None
        await repo.expire(now + timedelta(days=30) - timedelta(microseconds=1))
        assert await repo.usage() == (1, 0)
        await repo.expire(now + timedelta(days=30))
        assert await repo.get(asset.id) is None
        assert await repo.usage() == (0, 0)


async def test_upload_admission_refreshes_short_remaining_reservation(container, user):
    asset = await seed(container, user)
    now = asset.reservation_expires_at - timedelta(seconds=1)
    async with container.session_factory() as session:
        repo = SqlOriginalAssetRepository(session)
        assert await repo.begin_upload(asset.id, now)
        assert (await repo.get(asset.id)).reservation_expires_at == now + timedelta(minutes=2)
        await repo.expire(now + timedelta(seconds=60))
        assert await repo.pending_count() == 1
        assert await repo.activate(asset.id, b"data", now + timedelta(seconds=60))
