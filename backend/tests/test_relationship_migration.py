"""Disposable migration checks, including refusal before retained history is dropped."""

import asyncio
import sqlite3
from contextlib import closing
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
from ase.domain.claim_revisions import (
    ClaimCitationInput,
    ClaimKind,
    ClaimRelation,
    ClaimReviewState,
    revise_claim,
)
from legacy_annotation_history import seed_initial
from report_documents_helpers import document_records
from test_mfa_migration import prepare


async def populate_history(database, relationship):
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}")
    report, version = document_records(UUID(relationship))
    item = version.evidence[0]
    revision = revise_claim(
        version=version,
        revision_id=uuid4(),
        claim_id=uuid4(),
        previous=None,
        statement="The source reports an observation.",
        kind=ClaimKind.REPORTED_FACT,
        state=ClaimReviewState.PROPOSED,
        citations=(
            ClaimCitationInput(
                item.label, ClaimRelation.SUPPORTING, "title", 0, len(item.title), item.title
            ),
        ),
        unresolved_conflicts=(),
        reason="Preserve attributed evidence.",
        actor_id=UUID(relationship),
        now=version.created_at,
    )
    try:
        async with async_sessionmaker(engine)() as session:
            await SqlReportRepository(session).add(report, version)
            await seed_initial(session, revision, evidence_digest(version))
            await session.commit()
    finally:
        await engine.dispose()


def test_upgrade_preserves_existing_data_and_matches_models(tmp_path):
    config, database, relationship = prepare(tmp_path)
    command.upgrade(config, "0028")
    asyncio.run(populate_history(database, relationship))
    queries = (
        "SELECT * FROM users",
        "SELECT * FROM refresh_tokens",
        "SELECT * FROM claims",
        "SELECT * FROM claim_revisions",
        "SELECT * FROM reports",
        "SELECT * FROM report_versions",
    )
    with closing(sqlite3.connect(database)) as connection:
        before = {query: connection.execute(query).fetchall() for query in queries}
        assert all(before.values())
    command.upgrade(config, "0029")
    engine = sa.create_engine(f"sqlite:///{database}")
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(
                connection,
                opts={
                    "include_object": lambda obj, name, kind, reflected, comparison: (
                        kind != "table"
                        or name in {"relationship_reviews", "relationship_review_revisions"}
                    )
                },
            )
            assert compare_metadata(context, Base.metadata) == []
    finally:
        engine.dispose()
    command.downgrade(config, "0028")
    command.upgrade(config, "0029")
    with closing(sqlite3.connect(database)) as connection:
        for query, rows in before.items():
            assert connection.execute(query).fetchall() == rows
        assert connection.execute("SELECT count(*) FROM relationship_reviews").fetchone() == (0,)


@pytest.mark.parametrize("retained", ["root", "revision"])
def test_downgrade_refuses_either_retained_table_before_ddl(tmp_path, retained):
    config, database, relationship = prepare(tmp_path)
    command.upgrade(config, "0029")
    # Deliberately allow orphan rows to prove even damaged history prevents loss.
    with closing(sqlite3.connect(database)) as connection, connection:
        if retained == "root":
            connection.execute(
                "INSERT INTO relationship_reviews VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    "a" * 32,
                    "b" * 32,
                    "c" * 32,
                    relationship,
                    None,
                    "E1",
                    "d" * 64,
                    "e" * 32,
                    "2026-09-07T12:00:00Z",
                ),
            )
        else:
            connection.execute(
                "INSERT INTO relationship_review_revisions VALUES (?,?,?,?,?,?)",
                ("e" * 32, "a" * 32, 1, '{"preserve":"原文"}', "d" * 64, 20),
            )
        before = tuple(connection.iterdump())
    with pytest.raises(RuntimeError, match="Relationship history remains"):
        command.downgrade(config, "0028")
    with closing(sqlite3.connect(database)) as connection:
        assert tuple(connection.iterdump()) == before
