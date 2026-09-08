"""Actual FIRMS migration preserves existing state and refuses retained configuration loss."""

import asyncio
import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.firms_credentials import SqlFirmsCredentials
from ase.adapters.persistence.operational_models import AlertRow
from ase.domain.firms_credentials import FirmsCredential
from ase.infrastructure.migrations import alembic_config
from test_annotation_monitor_migration_postgres import snapshot
from test_llm_connections_migration import _seed


@pytest.fixture(params=["sqlite", "postgresql"])
async def migration_url(request, tmp_path):
    if request.param == "sqlite":
        yield f"sqlite+aiosqlite:///{tmp_path / 'firms.db'}"
        return
    source = os.environ.get("ASE_FIRMS_MIGRATION_POSTGRES_URL")
    if not source:
        pytest.skip("Set ASE_FIRMS_MIGRATION_POSTGRES_URL to an owned disposable PostgreSQL server")
    url = sa.make_url(source)
    assert url.drivername == "postgresql+asyncpg" and url.host in {"127.0.0.1", "localhost", "::1"}
    name = f"ase_firms_migration_{uuid4().hex}"
    admin = create_async_engine(url, isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as connection:
            await connection.execute(sa.text(f'CREATE DATABASE "{name}"'))
        try:
            yield url.set(database=name).render_as_string(hide_password=False)
        finally:
            async with admin.connect() as connection:
                await connection.execute(sa.text(f'DROP DATABASE "{name}"'))
    finally:
        await admin.dispose()


async def configured(url):
    config = alembic_config(url)
    await asyncio.to_thread(command.upgrade, config, "0031")
    engine = create_async_engine(url, poolclass=sa.NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(seed_existing)
        return config, engine
    except BaseException:
        await engine.dispose()
        raise


def seed_existing(connection):
    owner = UUID(str(_seed(connection)["owner"]))
    for origin in ("indicator", "schedule"):
        connection.execute(
            AlertRow.__table__.insert().values(
                id=uuid4(),
                indicator_id=uuid4() if origin == "indicator" else None,
                schedule_id=uuid4() if origin == "schedule" else None,
                fired_at=datetime(2026, 9, 8, tzinfo=UTC),
                title=origin,
                summary="Retained alert",
                count=1,
                threshold=1,
                event_ids=[],
                countries=[],
                acknowledged_at=datetime(2026, 9, 8, tzinfo=UTC),
                acknowledged_by=owner,
                created_by=owner,
            )
        )


def parity(connection):
    context = MigrationContext.configure(
        connection,
        opts={
            "include_object": lambda obj, name, kind, reflected, comparison: (
                kind != "table" or name == "firms_credentials"
            ),
        },
    )
    assert compare_metadata(context, Base.metadata) == []


async def test_firms_migration_preserves_all_old_rows_and_roundtrips(migration_url):
    config, engine = await configured(migration_url)
    try:
        async with engine.connect() as connection:
            columns, before = await connection.run_sync(snapshot)
        assert before["reports"] and len(before["alerts"]) == 2
        for _ in range(2):
            await asyncio.to_thread(command.upgrade, config, "0032")
            async with engine.connect() as connection:
                await connection.run_sync(parity)
                assert (await connection.run_sync(lambda sync: snapshot(sync, columns)))[
                    1
                ] == before
            await asyncio.to_thread(command.downgrade, config, "0031")
            async with engine.connect() as connection:
                assert await connection.run_sync(snapshot) == (columns, before)
    finally:
        await engine.dispose()


@pytest.mark.parametrize("retained", ["draft", "active", "cleared_history"])
async def test_retained_configuration_refuses_downgrade_without_changes(migration_url, retained):
    config, engine = await configured(migration_url)
    try:
        await asyncio.to_thread(command.upgrade, config, "0032")
        row = FirmsCredential(revision=1, active_revision=1)
        if retained == "draft":
            row.draft_encrypted = "synthetic-encrypted-draft"
        elif retained == "active":
            row.active_encrypted = "synthetic-encrypted-active"
        async with async_sessionmaker(engine)() as session:
            await SqlFirmsCredentials(session).save(row)
            await session.commit()
        async with engine.connect() as connection:
            before = await connection.run_sync(snapshot)
        with pytest.raises(RuntimeError, match="Refusing downgrade"):
            await asyncio.to_thread(command.downgrade, config, "0031")
        async with engine.connect() as connection:
            assert await connection.run_sync(snapshot) == before
            assert (
                await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
                == "0032"
            )
    finally:
        await engine.dispose()
