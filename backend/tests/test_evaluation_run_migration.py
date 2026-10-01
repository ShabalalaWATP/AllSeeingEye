"""Migration 0076 creates the evaluation run table with one active slot, and reverses."""

import importlib.util
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, MetaData, Table, Uuid, create_engine, inspect
from sqlalchemy.exc import IntegrityError

from ase.adapters.persistence.evaluation_run_models import EvaluationRunRow

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)


def _migration(connection):
    path = Path(__file__).parents[1] / "alembic/versions/0076_evaluation_runs.py"
    spec = importlib.util.spec_from_file_location("evaluation_runs_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(connection))
    return module


def _row(**values):
    row = {
        "id": uuid4(),
        "actor_id": None,
        "profile_id": uuid4(),
        "profile_name": "Fixture",
        "model": "fixture-model",
        "profile_fingerprint": "f" * 64,
        "case_ids": ["conflicting_reports"],
        "case_fingerprints": {"conflicting_reports": "a" * 64},
        "max_calls": 4,
        "status": "running",
        "active_slot": 1,
        "cancel_requested": False,
        "calls_reserved": 0,
        "calls_failed": 0,
        "results": [],
        "created_at": NOW,
        "lease_expires_at": NOW,
    }
    row.update(values)
    return row


def test_evaluation_run_migration_enforces_one_active_run_and_downgrades() -> None:
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        Table("users", MetaData(), Column("id", Uuid(), primary_key=True)).create(connection)
        migration = _migration(connection)
        assert migration.revision == "0076" and migration.down_revision == "0066"
        migration.upgrade()
        table = EvaluationRunRow.__table__
        connection.execute(table.insert().values(**_row()))
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(table.insert().values(**_row()))
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(table.insert().values(**_row(status="completed")))
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                table.insert().values(**_row(active_slot=None, status="stopped", max_calls=0))
            )
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                table.insert().values(**_row(active_slot=None, status="stopped", calls_reserved=9))
            )
        # Finished runs release the slot, so any number of them may coexist.
        for _ in range(2):
            connection.execute(table.insert().values(**_row(active_slot=None, status="completed")))
        assert "evaluation_runs" in inspect(connection).get_table_names()
        migration.downgrade()
        assert "evaluation_runs" not in inspect(connection).get_table_names()
        migration.upgrade()
        assert "evaluation_runs" in inspect(connection).get_table_names()
