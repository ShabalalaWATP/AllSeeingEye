"""Recovery-code migration guards use a disposable SQLite database only."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic import command

from test_mfa_migration import prepare


def test_recovery_upgrade_and_lossless_empty_downgrade(tmp_path: Path) -> None:
    config, database, identity = prepare(tmp_path)
    command.upgrade(config, "0021")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT count(*) FROM mfa_recovery_codes").fetchone() == (0,)
        assert connection.execute("SELECT id FROM users").fetchone() == (identity,)
    command.downgrade(config, "0020")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0020",)


def test_recovery_downgrade_does_not_silently_discard_codes(tmp_path: Path) -> None:
    config, database, identity = prepare(tmp_path)
    command.upgrade(config, "0021")
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO mfa_recovery_codes(code_hash,user_id,security_version) VALUES(?,?,?)",
            ("a" * 64, identity, 0),
        )
    with pytest.raises(RuntimeError, match="Recovery codes remain configured"):
        command.downgrade(config, "0020")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0021",)
        assert connection.execute("SELECT count(*) FROM mfa_recovery_codes").fetchone() == (1,)
