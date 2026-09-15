"""Team migration preserves accounts without assigning them to invented shared groups."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from alembic import command

from ase.infrastructure.migrations import alembic_config


def test_team_upgrade_and_downgrade_preserve_existing_account(tmp_path: Path) -> None:
    database = tmp_path / "team-migration.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0012")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "INSERT INTO users (id,email,display_name,role,is_active,failed_login_count,"
            "created_at,security_version) VALUES (?,?,?,?,?,?,?,?)",
            ("1" * 32, "existing@example.com", "Existing", "user", 1, 0, "2026-09-06", 0),
        )
        connection.commit()
    command.upgrade(config, "0013")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT email FROM users").fetchall() == [
            ("existing@example.com",)
        ]
        assert connection.execute("SELECT * FROM teams").fetchall() == []
        assert connection.execute("SELECT * FROM team_memberships").fetchall() == []
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(
            "INSERT INTO teams VALUES (?,?,?,?,?,?)",
            ("2" * 32, "Desk", 1, "1" * 32, "2026-09-06", "2026-09-06"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO team_memberships VALUES (?,?,?,?)",
                ("2" * 32, "1" * 32, "admin", "2026-09-06"),
            )
        connection.commit()
    command.downgrade(config, "0012")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT email FROM users").fetchall() == [
            ("existing@example.com",)
        ]
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
        assert not {"teams", "team_memberships"} & tables


def test_creator_manager_backfill_assigns_only_active_creators(tmp_path: Path) -> None:
    database = tmp_path / "team-creator-backfill.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0034")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "INSERT INTO users (id,email,display_name,role,is_active,failed_login_count,"
            "created_at,security_version) VALUES (?,?,?,?,?,?,?,?)",
            ("a" * 32, "active@example.com", "Active", "user", 1, 0, "2026-09-06", 0),
        )
        connection.execute(
            "INSERT INTO users (id,email,display_name,role,is_active,failed_login_count,"
            "created_at,security_version) VALUES (?,?,?,?,?,?,?,?)",
            ("i" * 32, "inactive@example.com", "Inactive", "user", 0, 0, "2026-09-06", 0),
        )
        connection.execute(
            "INSERT INTO teams VALUES (?,?,?,?,?,?)",
            ("1" * 32, "Active desk", 1, "a" * 32, "2026-09-06", "2026-09-06"),
        )
        connection.execute(
            "INSERT INTO teams VALUES (?,?,?,?,?,?)",
            ("2" * 32, "Inactive desk", 1, "i" * 32, "2026-09-06", "2026-09-06"),
        )
        connection.execute(
            "INSERT INTO teams VALUES (?,?,?,?,?,?)",
            ("3" * 32, "Existing member desk", 1, "a" * 32, "2026-09-06", "2026-09-06"),
        )
        connection.execute(
            "INSERT INTO team_memberships VALUES (?,?,?,?)",
            ("3" * 32, "a" * 32, "member", "2026-09-06"),
        )
        connection.commit()
    command.upgrade(config, "0047")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT team_id,user_id,role FROM team_memberships ORDER BY team_id"
        ).fetchall() == [
            ("1" * 32, "a" * 32, "manager"),
            ("3" * 32, "a" * 32, "manager"),
        ]
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            ("ix_team_memberships_team_role",),
        ).fetchone() == ("ix_team_memberships_team_role",)


def test_retire_global_manager_preserves_security_version_boundary(tmp_path: Path) -> None:
    database = tmp_path / "retire-global-manager.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0049")
    with closing(sqlite3.connect(database)) as connection:
        connection.execute(
            "INSERT INTO users (id,email,display_name,role,is_active,failed_login_count,"
            "created_at,security_version) VALUES (?,?,?,?,?,?,?,?)",
            ("m" * 32, "legacy-manager@example.com", "Legacy", "manager", 1, 0, "2026-09-06", 4),
        )
        connection.execute(
            "INSERT INTO teams (id,name,is_active,created_by,created_at,updated_at,description) "
            "VALUES (?,?,?,?,?,?,?)",
            ("t" * 32, "Legacy desk", 1, "m" * 32, "2026-09-06", "2026-09-06", None),
        )
        connection.execute(
            "INSERT INTO team_memberships (team_id,user_id,role,joined_at) VALUES (?,?,?,?)",
            ("t" * 32, "m" * 32, "manager", "2026-09-06"),
        )
        connection.commit()
    command.upgrade(config, "0050")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT role,security_version FROM users WHERE email=?",
            ("legacy-manager@example.com",),
        ).fetchone() == ("user", 5)
        assert connection.execute(
            "SELECT role FROM team_memberships WHERE user_id=?", ("m" * 32,)
        ).fetchone() == ("manager",)
