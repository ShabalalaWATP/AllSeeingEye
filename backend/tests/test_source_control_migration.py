"""Source activation upgrades preserve legacy accounts and reject lossy downgrades."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic import command

from test_mfa_migration import prepare


def test_source_controls_legacy_upgrade_and_empty_downgrade(tmp_path: Path) -> None:
    config, database, identity = prepare(tmp_path)
    command.upgrade(config, "0022")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT id FROM users").fetchone() == (identity,)
        assert connection.execute("SELECT count(*) FROM source_controls").fetchone() == (0,)
    command.downgrade(config, "0021")


def test_source_controls_nonempty_downgrade_is_refused(tmp_path: Path) -> None:
    config, database, identity = prepare(tmp_path)
    command.upgrade(config, "0022")
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO source_controls VALUES (?,?,?,?)",
            ("source", False, "2026-09-06T12:00:00Z", identity),
        )
    with pytest.raises(RuntimeError, match="Source activation overrides"):
        command.downgrade(config, "0021")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT count(*) FROM source_controls").fetchone() == (1,)
