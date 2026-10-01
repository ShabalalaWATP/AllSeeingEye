"""Disposable additive reminder migration and offline PostgreSQL DDL."""

from io import StringIO

import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config


def test_reminder_receipt_migration(tmp_path):
    database = tmp_path / "forecast-reminders.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database.as_posix()}")
    command.upgrade(config, "0085")
    command.upgrade(config, "0086")
    engine = sa.create_engine(f"sqlite:///{database.as_posix()}")
    try:
        inspector = sa.inspect(engine)
        assert inspector.get_pk_constraint("forecast_review_reminders")["constrained_columns"] == [
            "version_id",
            "review_at",
        ]
        assert (
            inspector.get_foreign_keys("forecast_review_reminders")[0]["referred_table"]
            == "report_ledger_heads"
        )
        command.downgrade(config, "0085")
        assert "forecast_review_reminders" not in sa.inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_postgres_reminder_ddl():
    config = alembic_config("postgresql+asyncpg://fixture:fixture@localhost/unused")
    output = StringIO()
    config.output_buffer = output
    command.upgrade(config, "0085:0086", sql=True)
    assert "CREATE TABLE forecast_review_reminders" in output.getvalue()
    assert "PRIMARY KEY (version_id, review_at)" in output.getvalue()
