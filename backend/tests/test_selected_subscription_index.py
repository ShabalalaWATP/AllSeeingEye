"""Selected metadata index behaviour on disposable in-memory SQLite."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ase.adapters.persistence import models as _models  # noqa: F401
from ase.adapters.persistence import teams as _teams  # noqa: F401
from ase.adapters.persistence.base import Base
from ase.adapters.persistence.operational_models import ScheduleRow
from ase.adapters.persistence.selected_index_models import SelectedIndexGateRow
from ase.adapters.persistence.selected_subscription_index import (
    SqlSelectedSubscriptionIndexRepository,
)
from ase.domain.errors import Conflict
from ase.domain.selected_subscription_index import SelectedIndexLimits, SelectedMetadata

NOW = datetime(2026, 9, 14, 12, tzinfo=UTC)


def _record(key: str, *, version: str = "v1", retention_days: int = 30) -> SelectedMetadata:
    return SelectedMetadata(
        source_id="usgs",
        item_key=key,
        origin_key=key,
        source_version=version,
        title=f"Public event {key}",
        content_sha256=("a" if version == "v1" else "b") * 64,
        policy_id="usgs-public-v1",
        retention_days=retention_days,
        retrieved_at=NOW,
        published_at=NOW - timedelta(hours=1),
    )


def _schedule(subscription_id: UUID, owner_id: UUID, team_id: UUID | None = None) -> ScheduleRow:
    return ScheduleRow(
        id=subscription_id,
        team_id=team_id,
        name="Selected subscription",
        template_id="intsum",
        hour_utc=6,
        cadence="daily",
        created_by=owner_id,
        created_at=NOW,
        next_run_at=NOW + timedelta(days=1),
        enabled=True,
    )


async def _database():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker.begin() as session:
        session.add(SelectedIndexGateRow(id=1, revision=0))
    return engine, maker


async def _page(
    repo: SqlSelectedSubscriptionIndexRepository,
    subscription_id: UUID,
    owner_id: UUID,
    *,
    revision: int,
    page_key: str,
    records: tuple[SelectedMetadata, ...],
    now: datetime = NOW,
    limits: SelectedIndexLimits | None = None,
    team_ids: tuple[UUID, ...] = (),
) -> int:
    return await repo.persist_page(
        subscription_id,
        "usgs",
        actor_id=owner_id,
        authorised_team_ids=team_ids,
        expected_revision=revision,
        page_key=page_key,
        records=records,
        cursor_value=page_key,
        watermark_at=NOW,
        now=now,
        limits=limits or SelectedIndexLimits(),
    )


@pytest.mark.asyncio
async def test_page_and_cursor_rollback_together() -> None:
    engine, maker = await _database()
    try:
        owner, subscription_id = uuid4(), uuid4()
        async with maker.begin() as session:
            session.add(_schedule(subscription_id, owner))
        with pytest.raises(RuntimeError):
            async with maker.begin() as session:
                await _page(
                    SqlSelectedSubscriptionIndexRepository(session),
                    subscription_id,
                    owner,
                    revision=0,
                    page_key="p1",
                    records=(_record("a"),),
                )
                raise RuntimeError("simulate failure before caller commit")
        async with maker() as session:
            repo = SqlSelectedSubscriptionIndexRepository(session)
            assert await repo.get_cursor(subscription_id, "usgs", actor_id=owner) is None
            assert await repo.list_records(subscription_id, actor_id=owner) == ()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_replay_dedupe_and_correction_keep_distinct_versions() -> None:
    engine, maker = await _database()
    try:
        owner, subscription_id = uuid4(), uuid4()
        async with maker.begin() as session:
            session.add(_schedule(subscription_id, owner))
        async with maker.begin() as session:
            repo = SqlSelectedSubscriptionIndexRepository(session)
            original = _record("a")
            assert (
                await _page(
                    repo, subscription_id, owner, revision=0, page_key="p1", records=(original,)
                )
                == 1
            )
            assert (
                await _page(
                    repo, subscription_id, owner, revision=0, page_key="p1", records=(original,)
                )
                == 1
            )
            with pytest.raises(Conflict):
                await _page(
                    repo, subscription_id, owner, revision=0, page_key="p1", records=(_record("b"),)
                )
            assert (
                await _page(
                    repo, subscription_id, owner, revision=1, page_key="p2", records=(original,)
                )
                == 2
            )
            assert (
                await _page(
                    repo,
                    subscription_id,
                    owner,
                    revision=2,
                    page_key="p3",
                    records=(_record("a", version="v2"),),
                )
                == 3
            )
        async with maker() as session:
            repo = SqlSelectedSubscriptionIndexRepository(session)
            rows = await repo.list_records(subscription_id, actor_id=owner)
            assert len(rows) == 2
            assert rows[0].corrects_id == rows[1].id
            assert rows[0].corrects_fingerprint == rows[1].fingerprint
            assert rows[0].fingerprint != rows[1].fingerprint
            assert (await repo.get_cursor(subscription_id, "usgs", actor_id=owner)).revision == 3
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_owner_item_byte_and_age_eviction_record_coverage_loss() -> None:
    engine, maker = await _database()
    try:
        owner, subscription_id = uuid4(), uuid4()
        async with maker.begin() as session:
            session.add(_schedule(subscription_id, owner))
        async with maker.begin() as session:
            repo = SqlSelectedSubscriptionIndexRepository(session)
            assert (
                await _page(
                    repo,
                    subscription_id,
                    owner,
                    revision=0,
                    page_key="p1",
                    records=(_record("a"), _record("b")),
                    limits=SelectedIndexLimits(owner_records=2),
                )
                == 1
            )
            assert (
                await _page(
                    repo,
                    subscription_id,
                    owner,
                    revision=1,
                    page_key="p2",
                    records=(_record("c"),),
                    limits=SelectedIndexLimits(owner_records=2),
                )
                == 2
            )
            assert len(await repo.list_records(subscription_id, actor_id=owner)) == 2
            assert (
                await _page(
                    repo,
                    subscription_id,
                    owner,
                    revision=2,
                    page_key="p3",
                    records=(_record("d"),),
                    limits=SelectedIndexLimits(owner_bytes=_record("d").stored_bytes + 1),
                )
                == 3
            )
            assert len(await repo.list_records(subscription_id, actor_id=owner)) == 1
            assert (
                await _page(
                    repo,
                    subscription_id,
                    owner,
                    revision=3,
                    page_key="p4",
                    records=(),
                    now=NOW + timedelta(days=2),
                    limits=SelectedIndexLimits(max_age_days=1),
                )
                == 4
            )
            assert await repo.list_records(subscription_id, actor_id=owner) == ()
            losses = await repo.list_losses(subscription_id, actor_id=owner)
            assert {row.reason: row.lost_items for row in losses} == {
                "owner_item_cap": 1,
                "owner_byte_cap": 2,
                "age": 1,
            }
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_global_cap_rejects_page_without_cross_tenant_eviction_or_cursor_change() -> None:
    engine, maker = await _database()
    try:
        owner_a, owner_b, sub_a, sub_b = uuid4(), uuid4(), uuid4(), uuid4()
        async with maker.begin() as session:
            session.add_all((_schedule(sub_a, owner_a), _schedule(sub_b, owner_b)))
        size = _record("a").stored_bytes
        limits = SelectedIndexLimits(aggregate_bytes=size + 10)
        async with maker.begin() as session:
            await _page(
                SqlSelectedSubscriptionIndexRepository(session),
                sub_a,
                owner_a,
                revision=0,
                page_key="p1",
                records=(_record("a"),),
                limits=limits,
            )
        async with maker.begin() as session:
            with pytest.raises(Conflict):
                await _page(
                    SqlSelectedSubscriptionIndexRepository(session),
                    sub_b,
                    owner_b,
                    revision=0,
                    page_key="p1",
                    records=(_record("b"),),
                    limits=limits,
                )
        async with maker() as session:
            repo = SqlSelectedSubscriptionIndexRepository(session)
            assert len(await repo.list_records(sub_a, actor_id=owner_a)) == 1
            assert await repo.list_records(sub_b, actor_id=owner_b) == ()
            assert await repo.get_cursor(sub_b, "usgs", actor_id=owner_b) is None
    finally:
        await engine.dispose()


def test_metadata_validation_rejects_unbounded_or_non_permitted_payload() -> None:
    with pytest.raises(ValueError):
        SelectedIndexLimits(owner_records=50_001)
    with pytest.raises(ValueError):
        _record("a", retention_days=401)
    with pytest.raises(ValueError):
        SelectedMetadata(
            source_id="private query?x=secret",
            item_key="a",
            origin_key="a",
            source_version="v1",
            title="Event",
            content_sha256="a" * 64,
            policy_id="reviewed",
            retention_days=30,
            retrieved_at=NOW,
        )
