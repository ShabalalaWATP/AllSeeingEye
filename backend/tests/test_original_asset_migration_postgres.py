"""Opt-in original-asset migration parity on a generated disposable PostgreSQL DB."""

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.original_assets import SqlOriginalAssetRepository
from ase.adapters.persistence.reports import SqlReportRepository
from ase.domain.original_assets import OriginalAsset
from ase.infrastructure.migrations import alembic_config
from report_documents_helpers import document_records
from test_identity_migration_postgres import seed_owner, snapshot
from test_llm_connections_migration import _database


def assert_asset_schema(connection):
    context = MigrationContext.configure(
        connection,
        opts={
            "include_object": lambda obj, name, kind, reflected, comparison: (
                kind != "table" or name == "original_assets"
            )
        },
    )
    assert compare_metadata(context, Base.metadata) == []


def test_postgres_asset_upgrade_preserves_reports_and_refuses_data_loss(tmp_path):
    async def run():
        # Helper creates and drops only its generated DB, never the configured DB.
        async with _database("postgresql", tmp_path) as url:
            config = alembic_config(url)
            await asyncio.to_thread(command.upgrade, config, "0026")
            engine = create_async_engine(url)
            sessions = async_sessionmaker(engine)
            try:
                async with engine.begin() as connection:
                    owner = await connection.run_sync(seed_owner)
                record, version = document_records(owner)
                async with sessions() as session:
                    await SqlReportRepository(session).add(record, version)
                    await session.commit()
                async with engine.connect() as connection:
                    before = await connection.run_sync(snapshot)
                await asyncio.to_thread(command.upgrade, config, "0027")
                async with engine.connect() as connection:
                    await connection.run_sync(assert_asset_schema)
                    assert await connection.run_sync(snapshot) == before
                await asyncio.to_thread(command.downgrade, config, "0026")
                await asyncio.to_thread(command.upgrade, config, "0027")
                now = datetime.now(UTC)
                asset = OriginalAsset(
                    uuid4(),
                    record.id,
                    version.id,
                    version.number,
                    "E1",
                    "research_import",
                    "original-event",
                    hashlib.sha256(b"data").hexdigest(),
                    4,
                    "source.txt",
                    "text/plain",
                    "Owned synthetic original",
                    owner,
                    None,
                    owner,
                    now,
                    now + timedelta(days=30),
                    now + timedelta(minutes=2),
                    session_family_id=uuid4(),
                )
                async with sessions() as session:
                    repository = SqlOriginalAssetRepository(session)
                    await repository.create(asset)
                    assert await repository.begin_upload(asset.id, now)
                    assert await repository.activate(asset.id, b"data", now)
                    await session.commit()
                with pytest.raises(RuntimeError, match="Original asset records remain"):
                    await asyncio.to_thread(command.downgrade, config, "0026")
                async with sessions() as session:
                    retained = await SqlOriginalAssetRepository(session).content(asset.id)
                    assert retained is not None and retained.content == b"data"
                async with engine.connect() as connection:
                    assert await connection.run_sync(snapshot) == before
                    assert (
                        await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
                        == "0027"
                    )
            finally:
                await engine.dispose()

    asyncio.run(run())
