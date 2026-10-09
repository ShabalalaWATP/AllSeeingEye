"""Exercise this migration in a disposable database while its parent is integrated."""

import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_enquiry_migration_preserves_populated_tables_on_downgrade():
    path = Path(__file__).parents[1] / "alembic/versions/0093_enterprise_enquiries.py"
    spec = importlib.util.spec_from_file_location("enquiry_migration", path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.revision == "0093" and migration.down_revision == "0092"
    engine = create_engine("sqlite:///:memory:")
    try:
        with (
            engine.begin() as connection,
            Operations.context(MigrationContext.configure(connection)),
        ):
            migration.upgrade()
            columns = {
                item["name"] for item in inspect(connection).get_columns("enterprise_enquiries")
            }
            assert "ip" not in columns and "email" in columns
            connection.execute(
                text(
                    "INSERT INTO enterprise_enquiries "
                    "(id, name, email, organisation, role, deployment_interest, expected_users, "
                    "message, status, created_at, updated_at, submission_key) VALUES "
                    "(:id, 'Example', 'example@example.com', 'Example', '', 'undecided', '1_10', "
                    "'', 'new', '2026-10-09', '2026-10-09', :key)"
                ),
                {"id": uuid4().hex, "key": "a" * 64},
            )
            with pytest.raises(RuntimeError, match="before downgrading"):
                migration.downgrade()
            assert connection.scalar(text("SELECT COUNT(*) FROM enterprise_enquiries")) == 1
            # The test alone explicitly clears its synthetic row before testing empty downgrade.
            connection.execute(text("DELETE FROM enterprise_enquiries"))
            migration.downgrade()
            assert "enterprise_enquiries" not in inspect(connection).get_table_names()
    finally:
        engine.dispose()
