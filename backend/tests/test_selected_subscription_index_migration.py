"""Additive E04 schema on a disposable SQLite database only."""

from pathlib import Path

import sqlalchemy as sa
from alembic import command

from ase.infrastructure.migrations import alembic_config


def test_selected_index_upgrade_and_empty_downgrade(tmp_path: Path) -> None:
    database = tmp_path / "e04-selected-index-disposable.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0038")
    engine = sa.create_engine(f"sqlite:///{database}")
    try:
        before = set(sa.inspect(engine).get_table_names())
        command.upgrade(config, "0039")
        added = set(sa.inspect(engine).get_table_names()) - before
        assert added == {
            "selected_index_gate",
            "selected_index_cursors",
            "selected_index_records",
            "selected_index_losses",
        }
        with engine.connect() as connection:
            assert (
                connection.scalar(sa.text("SELECT revision FROM selected_index_gate WHERE id = 1"))
                == 0
            )
            assert connection.scalar(sa.text("SELECT count(*) FROM selected_index_records")) == 0
        command.downgrade(config, "0038")
        assert set(sa.inspect(engine).get_table_names()) == before
    finally:
        engine.dispose()
