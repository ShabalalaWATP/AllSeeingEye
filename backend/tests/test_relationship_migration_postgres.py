"""Opt-in PostgreSQL 0029 acceptance on newly generated, disposable databases only."""

import asyncio
import os
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ase.adapters.persistence.base import Base
from ase.adapters.persistence.reports import SqlReportRepository
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.relationship_review import revise_relationship_review
from ase.infrastructure.migrations import alembic_config
from legacy_annotation_history import seed_initial
from report_documents_helpers import document_records
from test_llm_connections_migration import _seed
from test_relationship_review import arguments

TABLES = {"relationship_reviews", "relationship_review_revisions"}


@pytest.fixture
async def migration_database():
    source = os.environ.get("ASE_RELATIONSHIP_MIGRATION_POSTGRES_URL")
    if not source:
        pytest.skip("Set ASE_RELATIONSHIP_MIGRATION_POSTGRES_URL to a disposable PG server")
    url = sa.make_url(source)
    assert url.drivername == "postgresql+asyncpg"
    assert url.host in {"127.0.0.1", "localhost", "::1"}
    name = f"ase_relationship_migration_{uuid4().hex}"
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


def snapshot(connection, names=None):
    metadata = sa.MetaData()
    metadata.reflect(connection)
    return {
        name: sorted(
            [dict(row) for row in connection.execute(sa.select(table)).mappings()],
            key=repr,
        )
        for name, table in metadata.tables.items()
        if names is None or name in names
    }


def schema_parity(connection):
    context = MigrationContext.configure(
        connection,
        opts={
            "include_object": lambda obj, name, kind, reflected, comparison: (
                kind != "table" or name in TABLES
            )
        },
    )
    assert compare_metadata(context, Base.metadata) == []
    inspector = sa.inspect(connection)
    assert {
        row["name"] for row in inspector.get_check_constraints("relationship_review_revisions")
    } == {"ck_relationship_revision_number", "ck_relationship_revision_bytes"}
    assert {
        tuple(row["column_names"])
        for row in inspector.get_unique_constraints("relationship_reviews")
    } == {("report_version_id", "evidence_label")}
    assert {
        tuple(row["column_names"])
        for row in inspector.get_unique_constraints("relationship_review_revisions")
    } == {("relationship_id", "number")}


async def test_postgres_upgrade_preserves_existing_rows_and_clean_roundtrip(migration_database):
    config = alembic_config(migration_database)
    await asyncio.to_thread(command.upgrade, config, "0028")
    engine = create_async_engine(migration_database, poolclass=sa.NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(_seed)
            before = await connection.run_sync(snapshot)
        for name in ("users", "teams", "reports", "report_versions", "llm_profiles", "llm_usage"):
            assert before[name], f"Preservation needs real seeded {name} rows"
        for _ in range(2):
            await asyncio.to_thread(command.upgrade, config, "0029")
            async with engine.connect() as connection:
                await connection.run_sync(schema_parity)
                current = await connection.run_sync(lambda sync: snapshot(sync, before))
                assert current.pop("alembic_version") == [{"version_num": "0029"}]
                assert current == {
                    key: rows for key, rows in before.items() if key != "alembic_version"
                }
                assert (
                    await connection.scalar(sa.text("SELECT count(*) FROM relationship_reviews"))
                    == 0
                )
            await asyncio.to_thread(command.downgrade, config, "0028")
            async with engine.connect() as connection:
                assert await connection.run_sync(snapshot) == before
                names = await connection.run_sync(lambda sync: sa.inspect(sync).get_table_names())
                assert not TABLES.intersection(names)
        await asyncio.to_thread(command.upgrade, config, "0029")
        async with engine.connect() as connection:
            await connection.run_sync(schema_parity)
    finally:
        await engine.dispose()


@pytest.mark.parametrize("retained", ["complete", "root", "orphan_revision"])
async def test_postgres_downgrade_refuses_retained_history_without_writes(
    migration_database, retained
):
    config = alembic_config(migration_database)
    await asyncio.to_thread(command.upgrade, config, "0029")
    engine = create_async_engine(migration_database, poolclass=sa.NullPool)
    try:
        async with engine.begin() as connection:
            seeded = await connection.run_sync(_seed)
        owner = UUID(str(seeded["owner"]))
        values = arguments()
        version = values["version"]
        report, _ = document_records(owner)
        report.id = version.report_id
        revision = revise_relationship_review(**{**values, "actor_id": owner})
        async with async_sessionmaker(engine)() as session:
            await SqlReportRepository(session).add(report, version)
            await seed_initial(session, revision, evidence_digest(version))
            await session.commit()
        async with engine.begin() as connection:
            if retained == "root":
                await connection.execute(sa.text("DELETE FROM relationship_review_revisions"))
            elif retained == "orphan_revision":
                # Owned synthetic DB only: prove damaged orphan history also blocks DDL.
                await connection.execute(sa.text("SET LOCAL session_replication_role = replica"))
                await connection.execute(sa.text("DELETE FROM relationship_reviews"))
            before = await connection.run_sync(snapshot)
        with pytest.raises(RuntimeError, match="Relationship history remains"):
            await asyncio.to_thread(command.downgrade, config, "0028")
        async with engine.connect() as connection:
            assert await connection.run_sync(snapshot) == before
            await connection.run_sync(schema_parity)
    finally:
        await engine.dispose()
