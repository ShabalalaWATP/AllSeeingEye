"""Disposable SQLite and PostgreSQL migration checks, including retained data guards."""

import importlib.util
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, Connection, MetaData, Table, Uuid, create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateSchema, DropSchema

from ase.adapters.persistence.research_usage_models import ResearchTierRow, ResearchUsageRow


def _exercise_migration(connection: Connection) -> None:
    path = Path(__file__).parents[1] / "alembic/versions/0065_research_tiers.py"
    spec = importlib.util.spec_from_file_location("research_tiers_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "0065" and module.down_revision == "0064"
    users = Table("users", MetaData(), Column("id", Uuid(), primary_key=True))
    users.create(connection)
    identity = uuid4()
    connection.execute(users.insert().values(id=identity))
    module.op = Operations(MigrationContext.configure(connection))
    module.upgrade()
    assert {"research_tiers", "research_usage"} <= set(inspect(connection).get_table_names())
    # PostgreSQL aborts a transaction after a failed statement, so isolate expected failures.
    with pytest.raises(IntegrityError), connection.begin_nested():
        connection.execute(
            ResearchTierRow.__table__.insert().values(user_id=identity, tier=5, revision=1)
        )
    connection.execute(
        ResearchTierRow.__table__.insert().values(user_id=identity, tier=4, revision=1)
    )
    connection.execute(
        ResearchUsageRow.__table__.insert().values(
            user_id=identity,
            period="day",
            period_start=datetime(2026, 9, 1, tzinfo=UTC),
            used=2,
        )
    )
    with pytest.raises(RuntimeError, match="research allowance records remain"):
        module.downgrade()
    connection.execute(ResearchTierRow.__table__.delete())
    connection.execute(ResearchUsageRow.__table__.delete())
    module.downgrade()
    assert "research_usage" not in inspect(connection).get_table_names()


def test_research_tier_migration_and_constraints():
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=ON"))
            _exercise_migration(connection)
    finally:
        engine.dispose()


async def test_research_tier_migration_on_postgres():
    source = os.environ.get("ASE_TEST_DATABASE_URL")
    if not source or not source.startswith("postgresql+asyncpg:"):
        pytest.skip("Set ASE_TEST_DATABASE_URL to a disposable PostgreSQL database")
    url = make_url(source)
    assert url.host in {"127.0.0.1", "localhost", "::1"}
    engine = create_async_engine(url)
    # A unique temporary schema prevents touching the fixture suite's existing public tables.
    schema = f"research_tier_migration_{uuid4().hex}"
    try:
        async with engine.begin() as connection:
            await connection.execute(CreateSchema(schema))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            await connection.run_sync(_exercise_migration)
            await connection.execute(DropSchema(schema, cascade=True))
        # On failure the outer transaction rolls back schema creation as well.
    finally:
        await engine.dispose()
