"""Library migrations preserve accounts and refuse a lossy rollback."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic import command

from test_mfa_migration import prepare


def test_library_upgrade_and_empty_downgrade(tmp_path: Path) -> None:
    config, database, identity = prepare(tmp_path)
    command.upgrade(config, "0023")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT id FROM users").fetchone() == (identity,)
        assert connection.execute("SELECT count(*) FROM research_library").fetchone() == (0,)
    command.downgrade(config, "0022")


def test_library_nonempty_downgrade_is_refused(tmp_path: Path) -> None:
    config, database, identity = prepare(tmp_path)
    command.upgrade(config, "0023")
    # This disposable raw connection does not enforce FKs; only rollback protection
    # is under test. Application tests exercise report ownership and deletion.
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO research_library VALUES (?,?,?,?,?)",
            (identity, "a" * 32, True, "Synthetic note", "2026-09-06T12:00:00Z"),
        )
    with pytest.raises(RuntimeError, match="Library entries remain"):
        command.downgrade(config, "0022")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT count(*) FROM research_library").fetchone() == (1,)
