"""Claim schema migration uses disposable SQLite and refuses retained-history loss."""

import sqlite3
from contextlib import closing

import pytest
from alembic import command

from test_mfa_migration import prepare


def test_upgrade_preserves_accounts_and_downgrade_refuses_history(tmp_path):
    config, database, identity = prepare(tmp_path)
    command.upgrade(config, "0025")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT id FROM users").fetchone() == (identity,)
        assert connection.execute("SELECT count(*) FROM claims").fetchone() == (0,)
    command.downgrade(config, "0024")
    command.upgrade(config, "0025")
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO claims VALUES (?,?,?,?,?,?,?,?)",
            (
                "a" * 32,
                "b" * 32,
                "c" * 32,
                identity,
                None,
                "d" * 64,
                "e" * 32,
                "2026-09-07T12:00:00Z",
            ),
        )
    with pytest.raises(RuntimeError, match="Claim history remains"):
        command.downgrade(config, "0024")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT count(*) FROM claims").fetchone() == (1,)
