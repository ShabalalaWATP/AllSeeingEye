"""Nightly encrypted PostgreSQL backups with retention, drills and optional off-site copies.

Designed for the operator's crontab; see docs/BACKUP_RESTORE.md. Subcommands:
  run      verified backup, encrypt, round-trip check, prune, optional off-site copy
  drill    decrypt the newest archive and authenticate it with restore.py --verify-only
  decrypt  recover an archive into a NEW directory for scripts/restore.py
"""

from __future__ import annotations

import argparse
import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import backup
import restore
from backup_archive import (
    archive_name,
    archives,
    decrypt,
    decrypted_sha256,
    encrypt,
    encryption_key,
    extract,
    heartbeat_url,
    pack,
    ping,
    prune,
    push_offsite,
    read_status,
    write_status,
)
from backup_bundle import BackupError

ROOT = Path(__file__).resolve().parents[1]
MIN_FREE_BYTES = 1024**3
FAILURES = (BackupError, OSError, subprocess.SubprocessError)


def log(message: str) -> None:
    print(f"{datetime.now(UTC):%Y-%m-%dT%H:%M:%SZ} {message}", flush=True)


@contextlib.contextmanager
def exclusive(root: Path) -> Iterator[None]:
    """One scheduled job at a time per backup root (the lock is Linux-only)."""
    try:
        import fcntl
    except ImportError:
        yield
        return
    with (root / ".lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BackupError("Another scheduled backup job is running.") from exc
        yield


def create(options: argparse.Namespace, work: Path, name: str) -> Path:
    """Build, encrypt and round-trip one archive, then move it into the root."""
    key = encryption_key(options.encryption_key_file)
    if shutil.disk_usage(options.root).free < MIN_FREE_BYTES:
        raise BackupError("Fewer than 1 GiB is free for backups.")
    bundle = work / name
    arguments = [
        "postgres",
        "--authentication-key-file",
        str(options.authentication_key_file),
    ]
    arguments += ["--output", str(bundle), "--compose-file", str(options.compose_file)]
    if backup.main(arguments) != 0:
        raise BackupError("The verified database backup did not complete.")
    expected = pack(bundle, work / f"{name}.tar")
    encrypted = work / f"{name}.tar.gpg"
    encrypt(work / f"{name}.tar", key, encrypted)
    if decrypted_sha256(encrypted, key) != expected:
        raise BackupError("The encrypted archive failed its round-trip check.")
    final = options.root / encrypted.name
    os.replace(encrypted, final)
    return final


def run(options: argparse.Namespace) -> int:
    started = datetime.now(UTC)
    status: dict[str, object] = {
        "attempted": started.isoformat(),
        "last_success": read_status(options.root).get("last_success"),
    }
    work = Path(tempfile.mkdtemp(prefix=".work-", dir=options.root))
    try:
        final = create(options, work, archive_name(started))
    except FAILURES as exc:
        message = str(exc) if isinstance(exc, BackupError) else "A backup step failed."
        return finish(options, status | {"result": "failed", "message": message})
    finally:
        shutil.rmtree(work, ignore_errors=True)
    status |= {"archive": final.name, "bytes": final.stat().st_size}
    status["last_success"] = started.isoformat()
    try:
        status["pruned"] = prune(options.root, options.keep)
        if options.offsite:
            push_offsite(final, options.offsite, options.offsite_port)
    except FAILURES as exc:
        message = (
            str(exc)
            if isinstance(exc, BackupError)
            else "Pruning or off-site copy failed."
        )
        return finish(
            options,
            status | {"result": "failed", "message": message + " Local archive kept."},
        )
    return finish(
        options, status | {"result": "ok", "message": "Encrypted and verified."}
    )


def finish(options: argparse.Namespace, status: dict[str, object]) -> int:
    failed = status["result"] != "ok"
    status["heartbeat_delivered"] = ping(options.heartbeat_url, failed=failed)
    write_status(options.root, status)
    log(
        f"Scheduled backup {status['result']}: {status['message']} {status.get('archive', '')}"
    )
    return 1 if failed else 0


def drill(options: argparse.Namespace) -> int:
    """Decrypt the newest archive and authenticate its manifest without touching Docker."""
    work = Path(tempfile.mkdtemp(prefix=".drill-", dir=options.root))
    try:
        found = archives(options.root)
        if not found:
            raise BackupError("No scheduled archive exists yet.")
        decrypt(
            found[-1], encryption_key(options.encryption_key_file), work / "bundle.tar"
        )
        bundle = extract(work / "bundle.tar", work)
        arguments = [str(bundle), "--verify-only"]
        arguments += ["--authentication-key-file", str(options.authentication_key_file)]
        if restore.main(arguments) != 0:
            raise BackupError("The decrypted bundle failed authenticated verification.")
    except FAILURES as exc:
        message = str(exc) if isinstance(exc, BackupError) else "A drill step failed."
        log(f"Restore drill failed: {message}")
        ping(options.heartbeat_url, failed=True)
        return 1
    finally:
        shutil.rmtree(work, ignore_errors=True)
    log(f"Restore drill passed for {found[-1].name}.")
    return 0


def recover(options: argparse.Namespace) -> int:
    """Decrypt one archive into a NEW directory, ready for scripts/restore.py."""
    try:
        options.output.mkdir(mode=0o700)
    except FileExistsError:
        log("Recovery output already exists; choose a new directory.")
        return 1
    tar_path = options.output / ".archive.tar"
    try:
        decrypt(options.archive, encryption_key(options.encryption_key_file), tar_path)
        bundle = extract(tar_path, options.output)
    except FAILURES as exc:
        log(
            f"Decryption failed: {exc if isinstance(exc, BackupError) else 'gpg failed.'}"
        )
        return 1
    finally:
        tar_path.unlink(missing_ok=True)
    log(f"Decrypted bundle ready at {bundle}")
    return 0


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    actions = command.add_subparsers(dest="action", required=True)
    for name in ("run", "drill"):
        action = actions.add_parser(name)
        action.add_argument(
            "--root", type=Path, required=True, help="Existing backup directory"
        )
        action.add_argument("--authentication-key-file", type=Path, required=True)
        action.add_argument("--encryption-key-file", type=Path, required=True)
        action.add_argument(
            "--heartbeat-url", type=heartbeat_url, help="Optional https monitor"
        )
    runner = actions.choices["run"]
    runner.add_argument(
        "--keep", type=int, default=30, help="Archives to keep (minimum 3)"
    )
    runner.add_argument(
        "--compose-file", type=Path, default=ROOT / "docker-compose.yml"
    )
    runner.add_argument("--offsite", help="Optional user@host:path reached over SSH")
    runner.add_argument("--offsite-port", type=int, default=22)
    recovery = actions.add_parser("decrypt")
    recovery.add_argument("archive", type=Path)
    recovery.add_argument("--encryption-key-file", type=Path, required=True)
    recovery.add_argument("--output", type=Path, required=True, help="New directory")
    return command


def main(argv: list[str] | None = None) -> int:
    try:
        options = parser().parse_args(argv)
    except BackupError as exc:
        log(str(exc))
        return 2
    if options.action == "decrypt":
        return recover(options)
    if not options.root.is_dir():
        log("The backup root must be an existing directory.")
        return 1
    try:
        with exclusive(options.root):
            return run(options) if options.action == "run" else drill(options)
    except BackupError as exc:
        log(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
