"""Compose PostgreSQL operations using fixed programs, argument lists and local sockets."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from backup_bundle import BackupError, digest, safe_path


def identifier(value: str) -> str:
    # A narrow subset avoids libpq connection strings and option-like arguments.
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", value):
        raise BackupError("PostgreSQL user/database names must be simple identifiers (63 max).")
    return value


@dataclass(frozen=True)
class ComposeDatabase:
    compose_file: Path
    user: str
    database: str

    def command(self, *arguments: str) -> list[str]:
        return [
            "docker",
            "compose",
            "--file",
            str(self.compose_file),
            "exec",
            "-T",
            "db",
            *arguments,
        ]


def run_command(
    command: list[str],
    *,
    incoming: BinaryIO | None = None,
    outgoing: BinaryIO | None = None,
    capture: bool = False,
) -> bytes:
    """Never echo driver errors, which may contain local configuration or credentials."""
    try:
        completed = subprocess.run(  # noqa: S603 - fixed executables, no shell
            command,
            stdin=incoming or subprocess.DEVNULL,
            stdout=subprocess.PIPE if capture else (outgoing or subprocess.DEVNULL),
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=600,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BackupError("PostgreSQL command failed; check Docker and db service access.") from exc
    return completed.stdout if capture else b""


def connect_compose(compose_file: Path) -> ComposeDatabase:
    compose_file = safe_path(compose_file)
    if not compose_file.is_file():
        raise BackupError("Compose configuration must be a file.")
    provisional = ComposeDatabase(compose_file, "", "")
    values = (
        run_command(provisional.command("printenv", "POSTGRES_USER", "POSTGRES_DB"), capture=True)
        .decode("utf-8")
        .splitlines()
    )
    if len(values) != 2:
        raise BackupError("Could not read the db service's user and database names.")
    return ComposeDatabase(compose_file, identifier(values[0]), identifier(values[1]))


def snapshot_postgres(database: ComposeDatabase, destination: Path) -> None:
    with destination.open("xb") as outgoing:
        destination.chmod(0o600)
        run_command(
            database.command(
                "pg_dump",
                "--username",
                database.user,
                "--dbname",
                database.database,
                "--format=custom",
                "--no-owner",
                "--no-acl",
                "--no-password",
            ),
            outgoing=outgoing,
        )
    digest(destination)


def restore_postgres(database: ComposeDatabase, source: Path, target_database: str) -> None:
    target_database = identifier(target_database)
    if target_database.casefold() in {
        database.database.casefold(),
        "postgres",
        "template0",
        "template1",
    }:
        raise BackupError("Choose a new database name, separate from the configured database.")
    with safe_path(source).open("rb") as incoming:
        # Validate the dump catalogue before creating anything in PostgreSQL.
        run_command(database.command("pg_restore", "--list"), incoming=incoming)
        incoming.seek(0)
        # createdb fails when the target exists. No DROP, --clean or overwrite option exists.
        run_command(
            database.command(
                "createdb",
                "--username",
                database.user,
                "--no-password",
                "--maintenance-db=postgres",
                "--template=template0",
                target_database,
            )
        )
        run_command(
            database.command(
                "pg_restore",
                "--username",
                database.user,
                "--no-password",
                "--dbname",
                target_database,
                "--no-owner",
                "--no-acl",
                "--single-transaction",
                "--exit-on-error",
            ),
            incoming=incoming,
        )
