"""Opt-in identity migration parity on a newly generated PostgreSQL database."""

import asyncio
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.identity_decisions import SqlIdentityDecisionRepository
from ase.adapters.persistence.reports import SqlReportRepository
from ase.domain.identity_review import revise_identity_decision
from ase.infrastructure.migrations import alembic_config
from legacy_annotation_history import seed_initial
from report_documents_helpers import document_records
from test_identity_review import arguments
from test_llm_connections_migration import _database
from test_scope_migration import _insert


def seed_owner(connection):
    metadata = sa.MetaData()
    metadata.reflect(connection, only=["users"])
    return UUID(_insert(connection, metadata.tables["users"], email="identity@example.test"))


def snapshot(connection):
    tables = sa.MetaData()
    tables.reflect(connection, only=["users", "reports", "report_versions"])
    return {
        name: [dict(row) for row in connection.execute(sa.select(table)).mappings()]
        for name, table in tables.tables.items()
    }


def assert_identity_schema(connection):
    context = MigrationContext.configure(
        connection,
        opts={
            "include_object": lambda obj, name, kind, reflected, comparison: (
                kind != "table" or name in {"identity_decisions", "identity_decision_revisions"}
            )
        },
    )
    assert compare_metadata(context, Base.metadata) == []


def test_postgres_identity_upgrade_and_retained_history_refusal(tmp_path):
    async def run():
        # Shared opt-in helper creates/drops only its generated database, never the supplied one.
        async with _database("postgresql", tmp_path) as url:
            config = alembic_config(url)
            await asyncio.to_thread(command.upgrade, config, "0025")
            engine = create_async_engine(url)
            try:
                async with engine.begin() as connection:
                    owner = await connection.run_sync(seed_owner)
                args = arguments()
                record, _ = document_records(owner)
                record.id = args["version"].report_id
                async with async_sessionmaker(engine)() as session:
                    await SqlReportRepository(session).add(record, args["version"])
                    await session.commit()
                async with engine.connect() as connection:
                    before = await connection.run_sync(snapshot)
                await asyncio.to_thread(command.upgrade, config, "0026")
                async with engine.connect() as connection:
                    await connection.run_sync(assert_identity_schema)
                    assert await connection.run_sync(snapshot) == before
                await asyncio.to_thread(command.downgrade, config, "0025")
                await asyncio.to_thread(command.upgrade, config, "0026")
                revision = revise_identity_decision(**{**args, "revision_id": uuid4()})
                async with async_sessionmaker(engine)() as session:
                    await seed_initial(session, revision, "a" * 64)
                    await session.commit()
                with pytest.raises(RuntimeError, match="Identity history remains"):
                    await asyncio.to_thread(command.downgrade, config, "0025")
                async with async_sessionmaker(engine)() as session:
                    retained = await SqlIdentityDecisionRepository(session).revision(
                        revision.decision_id, revision.id
                    )
                    assert retained == revision
                async with engine.connect() as connection:
                    assert await connection.run_sync(snapshot) == before
                    assert (
                        await connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
                        == "0026"
                    )
            finally:
                await engine.dispose()

    asyncio.run(run())
