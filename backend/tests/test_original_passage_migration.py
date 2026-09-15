"""The expiring original excerpt table is additive on a disposable database."""

import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config


def test_original_passage_migration_and_guarded_downgrade(tmp_path):
    database = tmp_path / "e02-migration.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0040")
    engine = sa.create_engine(f"sqlite:///{database}")
    try:
        command.upgrade(config, "0041")
        inspector = sa.inspect(engine)
        assert "original_passage_assets" in inspector.get_table_names()
        columns = {row["name"] for row in inspector.get_columns("original_passage_assets")}
        assert {
            "job_id",
            "report_version_id",
            "owner_id",
            "team_id",
            "snapshot",
            "snapshot_sha256",
            "expires_at",
        } <= columns
        assert any(
            set(row["constrained_columns"]) == {"report_version_id"}
            for row in inspector.get_foreign_keys("original_passage_assets")
        )
        command.downgrade(config, "0040")
        assert "original_passage_assets" not in sa.inspect(engine).get_table_names()
    finally:
        engine.dispose()
