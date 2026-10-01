"""Migration 0078 adds unique team copy provenance and reverses cleanly."""

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, MetaData, Table, Uuid, create_engine, inspect
from sqlalchemy.exc import IntegrityError

from ase.adapters.persistence.report_team_copy_models import ReportTeamCopyRow

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)


def _migration(connection):
    path = Path(__file__).parents[1] / "alembic/versions/0078_report_team_copies.py"
    spec = importlib.util.spec_from_file_location("report_team_copies_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(connection))
    return module


def _row(**values):
    row = {
        "id": uuid4(),
        "report_id": uuid4(),
        "team_id": uuid4(),
        "source_report_id": uuid4(),
        "source_version_id": uuid4(),
        "source_version_number": 1,
        "copied_by": uuid4(),
        "copied_at": NOW,
        "content_sha256": "a" * 64,
        "disclosed_labels": [],
        "omissions": [],
    }
    row.update(values)
    return row


def test_team_copy_migration_is_unique_per_version_and_team_and_downgrades() -> None:
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        metadata = MetaData()
        for name in ("users", "teams", "reports"):
            Table(name, metadata, Column("id", Uuid(), primary_key=True))
        metadata.create_all(connection)
        migration = _migration(connection)
        assert migration.revision == "0078" and migration.down_revision == "0077"
        migration.upgrade()
        table = ReportTeamCopyRow.__table__
        first = _row()
        connection.execute(table.insert().values(**first))
        duplicate = _row(source_version_id=first["source_version_id"], team_id=first["team_id"])
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(table.insert().values(**duplicate))
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(table.insert().values(**_row(report_id=first["report_id"])))
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(table.insert().values(**_row(source_version_number=0)))
        # The same version may be copied once to each different team.
        connection.execute(
            table.insert().values(**_row(source_version_id=first["source_version_id"]))
        )
        assert "report_team_copies" in inspect(connection).get_table_names()
        migration.downgrade()
        assert "report_team_copies" not in inspect(connection).get_table_names()
        migration.upgrade()
        assert "report_team_copies" in inspect(connection).get_table_names()
