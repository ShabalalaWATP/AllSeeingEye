"""Migration 0033 runs only against a fresh disposable SQLite database in these tests."""

import importlib.util
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

from ase.adapters.persistence.report_job_codec import payload_columns
from ase.adapters.persistence.report_job_models import ReportJobRow
from report_job_helpers import job


def migration():
    path = Path(__file__).parents[1] / "alembic/versions/0033_report_jobs.py"
    spec = importlib.util.spec_from_file_location("report_job_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_creates_constraints_and_refuses_to_drop_retained_jobs():
    module = migration()
    assert module.revision == "0033" and module.down_revision == "0032"
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            module.op = Operations(MigrationContext.configure(connection))
            module.upgrade()
            inspector = inspect(connection)
            unique = {
                tuple(item["column_names"])
                for item in inspector.get_unique_constraints("report_jobs")
            }
            assert ("owner_id", "request_key") in unique and ("version_id",) in unique
            value = job()
            connection.execute(
                ReportJobRow.__table__.insert().values(
                    id=value.id,
                    request_key=value.request_key,
                    owner_id=value.owner_id,
                    team_id=None,
                    title=value.title,
                    status=value.status,
                    stage=value.stage,
                    created_at=value.created_at,
                    updated_at=value.updated_at,
                    revision=value.revision,
                    lease_token=None,
                    lease_until=None,
                    report_id=value.report_id,
                    version_id=value.version_id,
                    error=None,
                    **payload_columns(value.payload),
                )
            )
            with pytest.raises(RuntimeError, match="retained report jobs"):
                module.downgrade()
            connection.execute(ReportJobRow.__table__.delete())
            module.downgrade()
            assert "report_jobs" not in inspect(connection).get_table_names()
    finally:
        engine.dispose()
