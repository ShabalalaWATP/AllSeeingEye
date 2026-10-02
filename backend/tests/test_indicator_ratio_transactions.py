"""Isolated persistence regressions for baseline cohorts and conditional rule edits."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ase.adapters.persistence.baselines import SqlBaselineRepository
from ase.adapters.persistence.models import ActivitySampleRow, Base, IndicatorRow
from ase.adapters.persistence.warning import SqlIndicatorRepository
from ase.domain.warning import Indicator

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)


@pytest_asyncio.fixture
async def sampled_rule():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync: Base.metadata.create_all(
                    sync, tables=[IndicatorRow.__table__, ActivitySampleRow.__table__]
                )
            )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        original = Indicator(
            id=uuid4(),
            name="Ratio",
            description="",
            plan_id=None,
            countries=(),
            bbox=None,
            categories=(),
            keywords=(),
            threshold=2,
            window_minutes=60,
            cooldown_minutes=60,
            severity_floor=0,
            report_template=None,
            enabled=True,
            created_by=uuid4(),
            created_at=NOW,
            updated_at=NOW,
            baseline_ratio=2.5,
            baseline_days=14,
            resumed_at=NOW - timedelta(days=8),
        )
        async with sessions() as session:
            await SqlIndicatorRepository(session).add(original)
            await SqlBaselineRepository(session).record("indicator", str(original.id), NOW, 3)
            await session.commit()
        yield sessions, original
    finally:
        await engine.dispose()


async def samples(session, rule):
    return list(
        await session.scalars(
            select(ActivitySampleRow.value).where(ActivitySampleRow.key == str(rule.id))
        )
    )


@pytest.mark.asyncio
async def test_losing_database_cas_does_not_delete_samples(sampled_rule, monkeypatch):
    sessions, original = sampled_rule
    winner = replace(original, name="Winning rename", updated_at=NOW + timedelta(seconds=1))
    async with sessions() as session:
        repository = SqlIndicatorRepository(session)
        assert await repository.save_if_unchanged(winner, original.updated_at)
        await session.commit()
    async with sessions() as session:
        repository = SqlIndicatorRepository(session)

        async def stale_read(_identifier):
            return original

        # Reproduce a writer that read before another writer committed its new revision.
        monkeypatch.setattr(repository, "get", stale_read)
        loser = replace(winner, keywords=("changed",))
        assert not await repository.save_if_unchanged(loser, original.updated_at)
        await session.commit()
    async with sessions() as session:
        assert await SqlIndicatorRepository(session).get(original.id) == winner
        assert await samples(session, original) == [3]


@pytest.mark.asyncio
async def test_semantic_reset_rolls_back_with_its_conditional_rule_write(sampled_rule):
    sessions, original = sampled_rule
    changed = replace(original, keywords=("changed",), updated_at=NOW + timedelta(seconds=1))
    async with sessions() as session:
        repository = SqlIndicatorRepository(session)
        assert await repository.save_if_unchanged(changed, original.updated_at)
        assert await samples(session, original) == []
        await session.rollback()
    async with sessions() as session:
        assert await SqlIndicatorRepository(session).get(original.id) == original
        assert await samples(session, original) == [3]


@pytest.mark.asyncio
async def test_successful_matching_edit_resets_only_its_rule(sampled_rule):
    sessions, original = sampled_rule
    other = replace(original, id=uuid4(), name="Other rule")
    async with sessions() as session:
        repository = SqlIndicatorRepository(session)
        await repository.add(other)
        await SqlBaselineRepository(session).record("indicator", str(other.id), NOW, 7)
        await session.commit()
        changed = replace(original, keywords=("changed",), updated_at=NOW + timedelta(seconds=1))
        assert await repository.save_if_unchanged(changed, original.updated_at)
        await session.commit()
    async with sessions() as session:
        assert await SqlIndicatorRepository(session).get(original.id) == changed
        assert await samples(session, original) == []
        assert await samples(session, other) == [7]
