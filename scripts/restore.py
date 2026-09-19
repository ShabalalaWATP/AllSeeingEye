"""Verify or restore an ASE bundle into a new location, without replacing live data."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from backup_bundle import (
    BackupError,
    authentication_key,
    restore_files,
    safe_path,
    verify_bundle,
)
from backup_postgres import connect_compose, identifier, restore_postgres

ROOT = Path(__file__).resolve().parents[1]


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Verify a backup or restore to NEW targets only.")
    command.add_argument("bundle", type=Path, help="Backup directory containing manifest.json")
    command.add_argument(
        "--verify-only", action="store_true", help="Read-only validation; no Docker"
    )
    command.add_argument(
        "--output", type=Path, help="New directory for recovered database/config files"
    )
    command.add_argument(
        "--target-database", help="New PostgreSQL database name; never an existing one"
    )
    command.add_argument("--compose-file", type=Path, default=ROOT / "docker-compose.yml")
    command.add_argument(
        "--authentication-key-file",
        type=Path,
        help="Independent HMAC key used when the PostgreSQL backup was created",
    )
    return command


def main(argv: list[str] | None = None) -> int:
    command = parser()
    options = command.parse_args(argv)
    if options.verify_only and (options.output or options.target_database):
        command.error("--verify-only does not accept restore targets")
    if not options.verify_only and options.output is None:
        command.error("--output is required unless --verify-only is used")
    try:
        bundle = safe_path(options.bundle)
        authentication = (
            authentication_key(options.authentication_key_file)
            if options.authentication_key_file is not None
            else None
        )
        manifest = verify_bundle(
            bundle,
            authentication=authentication,
            require_postgres_authentication=not options.verify_only,
        )
        postgres = manifest["backend"] == "postgres"
        if options.verify_only:
            if postgres and authentication is not None:
                sys.stdout.write("Backup authentication, structure and format verified.\n")
            else:
                sys.stdout.write("Backup hashes, structure and database format verified.\n")
            return 0
        if postgres != (options.target_database is not None):
            raise BackupError("--target-database is required only for PostgreSQL restores.")
        if postgres:
            identifier(options.target_database)
        output = restore_files(bundle, options.output, manifest)
        if postgres:
            restore_postgres(
                connect_compose(options.compose_file),
                output / "database.dump",
                options.target_database,
            )
    except (BackupError, OSError, sqlite3.Error, UnicodeError) as exc:
        message = str(exc) if isinstance(exc, BackupError) else "Restore input/output failed."
        sys.stderr.write(f"Restore failed: {message} Any new target may be incomplete.\n")
        return 1
    sys.stdout.write(
        "Restored to new targets. Configuration awaits manual review; services were not changed.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
