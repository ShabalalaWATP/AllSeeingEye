"""Team migration preserves accounts without assigning them to invented shared groups."""

import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import UUID

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
        # Authority granted without an interactive actor is inventoried per team.
        inventory = connection.execute(
            "SELECT subject, details FROM audit_log WHERE action='team_authority_migrated' "
            "ORDER BY subject"
        ).fetchall()
        assert [subject for subject, _ in inventory] == [
            f"team:{UUID('1' * 32)}",
            f"team:{UUID('3' * 32)}",
        ]
        assert "creator_membership_added" in inventory[0][1]
        assert "creator_membership_promoted" in inventory[1][1]
        assert all("@" not in details for _, details in inventory)


def _user(connection: sqlite3.Connection, key: str, role: str, active: int = 1) -> None:
    connection.execute(
        "INSERT INTO users (id,email,display_name,role,is_active,failed_login_count,"
        "created_at,security_version) VALUES (?,?,?,?,?,?,?,?)",
        (key * 32, f"{key}@example.com", key.upper(), role, active, 0, "2026-09-06", 4),
    )


def _team(connection: sqlite3.Connection, key: str, creator: str, active: int = 1) -> None:
    connection.execute(
        "INSERT INTO teams (id,name,is_active,created_by,created_at,updated_at,description) "
        "VALUES (?,?,?,?,?,?,?)",
        (key * 32, f"Desk {key}", active, creator * 32, "2026-09-06", "2026-09-06", None),
    )


def _member(connection: sqlite3.Connection, team: str, user: str, role: str) -> None:
    connection.execute(
        "INSERT INTO team_memberships (team_id,user_id,role,joined_at) VALUES (?,?,?,?)",
        (team * 32, user * 32, role, "2026-09-06"),
    )


def test_retire_global_manager_preserves_security_version_boundary(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    database = tmp_path / "retire-global-manager.db"
    config = alembic_config(f"sqlite+aiosqlite:///{database}")
    command.upgrade(config, "0049")
    with closing(sqlite3.connect(database)) as connection:
        _user(connection, "c", "manager")
        _user(connection, "e", "user")
        _user(connection, "a", "admin")
        _user(connection, "d", "manager", active=0)
        # Legacy manager account leading a team keeps that authority.
        _team(connection, "1", "c")
        _member(connection, "1", "c", "manager")
        _member(connection, "1", "e", "manager")
        # An ordinary account's Manager membership granted nothing before 0050.
        _team(connection, "2", "e")
        _member(connection, "2", "e", "manager")
        # Administrators keep their memberships.
        _team(connection, "5", "a")
        _member(connection, "5", "a", "manager")
        # Only an inactive legacy Manager: reported, not repaired.
        _team(connection, "3", "d")
        _member(connection, "3", "d", "manager")
        # Archived teams are not reported as unmanaged.
        _team(connection, "4", "e", active=0)
        _member(connection, "4", "e", "manager")
        connection.commit()
    with caplog.at_level("WARNING"):
        command.upgrade(config, "0050")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute(
            "SELECT role,security_version FROM users WHERE email=?",
            ("c@example.com",),
        ).fetchone() == ("user", 5)
        assert connection.execute("SELECT role FROM users WHERE id=?", ("e" * 32,)).fetchone() == (
            "user",
        )
        roles = dict(
            connection.execute(
                "SELECT team_id || ':' || user_id, role FROM team_memberships"
            ).fetchall()
        )
        assert roles == {
            f"{'1' * 32}:{'c' * 32}": "manager",
            f"{'1' * 32}:{'e' * 32}": "member",
            f"{'2' * 32}:{'e' * 32}": "member",
            f"{'5' * 32}:{'a' * 32}": "manager",
            f"{'3' * 32}:{'d' * 32}": "manager",
            f"{'4' * 32}:{'e' * 32}": "member",
        }
        inventory = connection.execute(
            "SELECT subject, details FROM audit_log WHERE action='team_authority_migrated'"
        ).fetchall()
    demoted = {subject for subject, details in inventory if "demoted" in details}
    unmanaged = {subject for subject, details in inventory if "without_active_manager" in details}
    assert demoted == {f"team:{UUID(key * 32)}" for key in ("1", "2", "4")}
    assert unmanaged == {f"team:{UUID(key * 32)}" for key in ("2", "3")}
    assert all("@" not in details for _, details in inventory)
    assert "2 active team(s) have no active Manager" in caplog.text
    assert "@example.com" not in caplog.text
