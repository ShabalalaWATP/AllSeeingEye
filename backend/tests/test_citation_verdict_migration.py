"""Migration 0077 adds the citation verdict table with its checks, and reverses cleanly."""

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, MetaData, Table, Uuid, create_engine, inspect
from sqlalchemy.exc import IntegrityError

from ase.adapters.persistence.citation_verdict_models import CitationVerdictRow

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)


def _migration(connection):
    path = Path(__file__).parents[1] / "alembic/versions/0077_citation_verdicts.py"
    spec = importlib.util.spec_from_file_location("citation_verdicts_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(connection))
    return module


def _row(**values):
    row = {
        "id": uuid4(),
        "report_id": uuid4(),
        "report_version_id": uuid4(),
        "version_number": 1,
        "judgement_id": "KJ1",
        "label": "E1",
        "relation": "supporting",
        "verdict": "supports",
        "note": None,
        "owner_id": uuid4(),
        "team_id": None,
        "reviewer_id": uuid4(),
        "recorded_at": NOW,
    }
    row.update(values)
    return row


def test_citation_verdict_migration_checks_values_and_downgrades() -> None:
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        metadata = MetaData()
        for name in ("users", "teams", "reports", "report_versions"):
            Table(name, metadata, Column("id", Uuid(), primary_key=True))
        metadata.create_all(connection)
        migration = _migration(connection)
        assert migration.revision == "0077" and migration.down_revision == "0076"
        migration.upgrade()
        table = CitationVerdictRow.__table__
        connection.execute(table.insert().values(**_row(note="Short reviewer note.")))
        for bad in (
            {"verdict": "true"},
            {"relation": "neutral"},
            {"note": "x" * 301},
            {"note": ""},
            {"version_number": 0},
        ):
            with pytest.raises(IntegrityError), connection.begin_nested():
                connection.execute(table.insert().values(**_row(**bad)))
        indexes = {row["name"] for row in inspect(connection).get_indexes("citation_verdicts")}
        assert {"ix_citation_verdicts_version", "ix_citation_verdicts_scope"} <= indexes
        migration.downgrade()
        assert "citation_verdicts" not in inspect(connection).get_table_names()
        assert "reports" in inspect(connection).get_table_names()
        migration.upgrade()
        assert "citation_verdicts" in inspect(connection).get_table_names()
