"""Create a new local backup bundle. Run `python scripts/backup.py --help`."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from backup_bundle import (
    DATABASE_FILES,
    BackupError,
    authentication_key,
    copy_configuration,
    new_directory,
    snapshot_sqlite,
    verify_bundle,
    write_manifest,
    write_manifest_signature,
)
from backup_postgres import connect_compose, snapshot_postgres

ROOT = Path(__file__).resolve().parents[1]


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Back up durable ASE data into a NEW directory.")
    command.add_argument("backend", choices=("sqlite", "postgres"))
    command.add_argument(
        "--output", type=Path, required=True, help="New directory; parent must exist"
    )
    command.add_argument(
        "--authentication-key-file",
        type=Path,
        help="Independent 32+ byte HMAC key file; required for PostgreSQL",
    )
    command.add_argument("--database", type=Path, help="SQLite file (required for sqlite)")
    command.add_argument(
        "--project-root", type=Path, default=ROOT, help="Configuration source root"
    )
    command.add_argument("--compose-file", type=Path, default=ROOT / "docker-compose.yml")
    command.add_argument(
        "--include-secrets",
        action="store_true",
        help="Explicitly include project .env in plaintext; excluded by default",
    )
    return command


def main(argv: list[str] | None = None) -> int:
    command = parser()
    options = command.parse_args(argv)
    if (options.backend == "sqlite") != (options.database is not None):
        command.error("--database is required for sqlite and is not used for postgres")
    if options.backend == "postgres" and options.authentication_key_file is None:
        command.error("--authentication-key-file is required for PostgreSQL")
    try:
        output = new_directory(options.output)
        copy_configuration(
            options.project_root,
            output,
            include_secrets=options.include_secrets,
            compose_file=options.compose_file if options.backend == "postgres" else None,
        )
        if options.backend == "sqlite":
            snapshot_sqlite(options.database, output / DATABASE_FILES["sqlite"])
        else:
            snapshot_postgres(
                connect_compose(options.compose_file), output / DATABASE_FILES["postgres"]
            )
        write_manifest(output, options.backend, include_secrets=options.include_secrets)
        if options.backend == "postgres":
            write_manifest_signature(output, authentication_key(options.authentication_key_file))
        verify_bundle(output)
    except (BackupError, OSError, sqlite3.Error, UnicodeError) as exc:
        # Do not include filesystem/driver errors, which may contain sensitive context.
        message = str(exc) if isinstance(exc, BackupError) else "Backup input/output failed."
        sys.stderr.write(f"Backup failed: {message} Any partial output is incomplete.\n")
        return 1
    sys.stdout.write(f"Verified {options.backend} backup created. Live events were excluded.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
