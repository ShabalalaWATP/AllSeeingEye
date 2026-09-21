"""Level 5 migration preserves assignments and counters on SQLite and PostgreSQL."""

import importlib.util
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, Connection, MetaData, Table, Uuid, create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from ase.adapters.persistence.research_usage_models import ResearchTierRow, ResearchUsageRow


def _migration(connection, name):
    path = Path(__file__).parents[1] / "alembic/versions" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(connection))
    return module


def _exercise(connection: Connection) -> None:
    users = Table("users", MetaData(), Column("id", Uuid(), primary_key=True))
    users.create(connection)
    identity = uuid4()
    connection.execute(users.insert().values(id=identity))
    previous = _migration(connection, "0065_research_tiers")
    previous.upgrade()
    current = _migration(connection, "0066_unlimited_research_tier")
    assert current.revision == "0066" and current.down_revision == "0065"
    tiers, usage = ResearchTierRow.__table__, ResearchUsageRow.__table__
    connection.execute(tiers.insert().values(user_id=identity, tier=4, revision=3))
    for period, used in (("day", 32), ("week", 70)):
        connection.execute(
            usage.insert().values(
                user_id=identity,
                period=period,
                period_start=datetime(2026, 9, 21, tzinfo=UTC),
                used=used,
            )
        )
    current.upgrade()
    assert connection.execute(select(tiers.c.tier, tiers.c.revision)).one() == (4, 3)
    assert dict(connection.execute(select(usage.c.period, usage.c.used)).all()) == {
        "day": 32,
        "week": 70,
    }
    # Savepoints keep PostgreSQL usable after an expected constraint failure.
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(tiers.update().values(tier=6))
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(tiers.update().values(revision=0))
    connection.execute(tiers.update().values(tier=5, revision=4))
    with pytest.raises(RuntimeError, match="Reassign Level 5 users"):
        current.downgrade()
    assert connection.execute(select(tiers.c.tier, tiers.c.revision)).one() == (5, 4)
    connection.execute(tiers.update().values(tier=2, revision=5))
    current.downgrade()
    assert connection.execute(select(tiers.c.tier, tiers.c.revision)).one() == (2, 5)
    assert dict(connection.execute(select(usage.c.period, usage.c.used)).all()) == {
        "day": 32,
        "week": 70,
    }
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(tiers.update().values(tier=5))
    # A round trip remains possible after an explicit reassignment.
    current.upgrade()
    connection.execute(tiers.update().values(tier=5, revision=6))
    assert connection.execute(select(tiers.c.tier, tiers.c.revision)).one() == (5, 6)


def test_unlimited_research_migration_preserves_existing_records():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=ON"))
            _exercise(connection)
    finally:
        engine.dispose()


async def test_unlimited_research_migration_on_postgres():
    source = os.environ.get("ASE_TEST_DATABASE_URL")
    if not source or not source.startswith("postgresql+asyncpg:"):
        pytest.skip("Set ASE_TEST_DATABASE_URL to a disposable PostgreSQL database")
    url = make_url(source)
    assert url.host in {"127.0.0.1", "localhost", "::1"}
    engine = create_async_engine(url)
    schema = f"unlimited_research_migration_{uuid4().hex}"
    try:
        async with engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            await connection.run_sync(_exercise)
            await connection.execute(DropSchema(schema, cascade=True))
        # Failed checks roll back the entire disposable schema without touching public tables.
    finally:
        await engine.dispose()
