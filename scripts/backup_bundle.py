"""Bounded, hash-verified backup directories, with no archive extraction or overwrites."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MAX_BYTES = 2 * 1024**3
MANIFEST_LIMIT = 64 * 1024
SIGNATURE_FILE = "manifest.hmac"
CONFIG_LIMIT = 1024**2
CONFIG_PATHS = (
    ".env.example",
    "docker-compose.yml",
    "infra/Caddyfile",
    "backend/src/ase/resources/social_watch.json",
    "backend/src/ase/resources/air_watch.json",
    "backend/src/ase/resources/conflicts.json",
)
DATABASE_FILES = {"sqlite": "database.sqlite3", "postgres": "database.dump"}
ALLOWED_FILES = {*(f"config/{name}" for name in CONFIG_PATHS), "config/.env"}
ALLOWED_FILES.update(DATABASE_FILES.values())


class BackupError(Exception):
    """A backup or restore failed without authorising destructive recovery."""


def safe_path(path: Path, *, must_exist: bool = True) -> Path:
    """Reject symlinks/junctions, including parents, before resolving an operator path."""
    absolute = path.absolute()
    for item in (absolute, *absolute.parents):
        if item.is_symlink() or item.is_junction():
            raise BackupError("Symbolic links and junctions are not supported.")
    if must_exist and not absolute.exists():
        raise BackupError("A required input path does not exist.")
    return absolute.resolve()


def new_directory(path: Path) -> Path:
    target = safe_path(path, must_exist=False)
    if not target.parent.is_dir():
        raise BackupError("The output parent directory must already exist.")
    try:
        target.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise BackupError("Output already exists; choose a new directory.") from exc
    return target


def digest(path: Path, limit: int = MAX_BYTES) -> tuple[int, str]:
    if not safe_path(path).is_file():
        raise BackupError("Backup members must be regular files.")
    total = 0
    result = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024**2):
            total += len(block)
            if total > limit:
                raise BackupError("Backup exceeds its size limit.")
            result.update(block)
    return total, result.hexdigest()


def copy_new(source: Path, destination: Path, limit: int = MAX_BYTES) -> None:
    safe_path(source)
    safe_path(destination, must_exist=False)
    expected = digest(source, limit)
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        destination.chmod(0o600)
        copied = 0
        while block := incoming.read(1024**2):
            copied += len(block)
            if copied > limit:
                raise BackupError("Backup exceeds its size limit.")
            outgoing.write(block)
    if digest(destination, limit) != expected:
        raise BackupError("Input changed while it was being copied.")


def copy_configuration(
    root: Path, output: Path, *, include_secrets: bool, compose_file: Path | None = None
) -> None:
    root = safe_path(root)
    for name in (*CONFIG_PATHS, *((".env",) if include_secrets else ())):
        source = compose_file if name == "docker-compose.yml" and compose_file else root / name
        safe_path(source, must_exist=False)
        if source.exists():
            copy_new(source, output / "config" / name, CONFIG_LIMIT)
        elif name == ".env":
            raise BackupError("--include-secrets requires a project .env file.")


def check_sqlite(path: Path) -> None:
    safe_path(path)
    try:
        # Bundles contain standalone snapshots. Immutable mode forbids WAL/SHM creation
        # even when an imported snapshot still carries a WAL-mode header.
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)) as database:
            database.enable_load_extension(False)
            if database.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
                raise BackupError("SQLite integrity check failed.")
    except sqlite3.Error as exc:
        raise BackupError("SQLite integrity check failed.") from exc


def snapshot_sqlite(source: Path, destination: Path) -> None:
    source = safe_path(source)
    if not source.is_file() or source.stat().st_size > MAX_BYTES:
        raise BackupError("SQLite source must be a file within the backup size limit.")
    deadline = time.monotonic() + 60

    def progress(_status: int, _remaining: int, total: int) -> None:
        if total * page_size > MAX_BYTES or time.monotonic() > deadline:
            raise BackupError("SQLite snapshot exceeded its page or time budget.")

    # Exclusive creation refuses even an empty pre-existing file.
    with destination.open("xb"):
        destination.chmod(0o600)
    try:
        with (
            closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original,
            closing(sqlite3.connect(destination)) as snapshot,
        ):
            page_size = original.execute("PRAGMA page_size").fetchone()[0]
            original.backup(snapshot, pages=256, progress=progress)
            snapshot.execute("PRAGMA journal_mode=DELETE")
        check_sqlite(destination)
    except sqlite3.Error as exc:
        raise BackupError("SQLite snapshot failed.") from exc


def write_manifest(output: Path, backend: str, *, include_secrets: bool) -> None:
    entries = []
    total = 0
    for path in sorted(output.rglob("*")):
        safe_path(path)
        if path.is_file():
            size, sha256 = digest(path)
            total += size
            entries.append(
                {"path": path.relative_to(output).as_posix(), "size": size, "sha256": sha256}
            )
    if total > MAX_BYTES:
        raise BackupError("Backup exceeds its total size limit.")
    manifest = {
        "version": 1,
        "backend": backend,
        "created_at": datetime.now(UTC).isoformat(),
        "includes_env": include_secrets,
        "files": entries,
    }
    with (output / "manifest.json").open("x", encoding="utf-8", newline="\n") as handle:
        (output / "manifest.json").chmod(0o600)
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def authentication_key(path: Path) -> bytes:
    """Load an independent binary HMAC key without accepting links or oversized files."""
    path = safe_path(path)
    if not path.is_file():
        raise BackupError("Backup authentication key must be a regular file.")
    with path.open("rb") as handle:
        key = handle.read(4_097)
    if not 32 <= len(key) <= 4_096:
        raise BackupError("Backup authentication key must contain 32 to 4096 bytes.")
    return key


def write_manifest_signature(output: Path, key: bytes) -> None:
    manifest = (output / "manifest.json").read_bytes()
    signature = hmac.new(key, manifest, hashlib.sha256).hexdigest()
    path = output / SIGNATURE_FILE
    path.write_text(signature + "\n", encoding="ascii", newline="\n")
    path.chmod(0o600)


def verify_manifest_signature(bundle: Path, key: bytes, manifest_bytes: bytes) -> None:
    bundle = safe_path(bundle)
    signature_path = bundle / SIGNATURE_FILE
    try:
        signature = signature_path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        raise BackupError("PostgreSQL backup authentication is missing or invalid.") from None
    if not re.fullmatch(r"[0-9a-f]{64}", signature):
        raise BackupError("PostgreSQL backup authentication is missing or invalid.")
    expected = hmac.new(key, manifest_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise BackupError("PostgreSQL backup authentication failed.")


def verify_entries(bundle: Path, manifest: dict[str, Any]) -> set[str]:
    """Check the allowlist, sizes and digests before considering database content."""
    entries = manifest.get("files")
    if not isinstance(entries, list) or not 1 <= len(entries) <= len(ALLOWED_FILES):
        raise BackupError("Invalid backup file list.")
    found: set[str] = set()
    total = 0
    for entry in entries:
        if not isinstance(entry, dict):
            raise BackupError("Invalid manifest entry.")
        name, size, sha256 = entry.get("path"), entry.get("size"), entry.get("sha256")
        if not isinstance(name, str) or name not in ALLOWED_FILES or name in found:
            raise BackupError("Unexpected or duplicate backup member.")
        if type(size) is not int or size < 0 or not isinstance(sha256, str):
            raise BackupError("Invalid member size or hash.")
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise BackupError("Invalid member hash.")
        total += size
        limit = CONFIG_LIMIT if name.startswith("config/") else MAX_BYTES
        if total > MAX_BYTES or size > limit:
            raise BackupError("Backup exceeds its size limit.")
        if digest(bundle / name, limit) != (size, sha256):
            raise BackupError("Backup hash or size mismatch.")
        found.add(name)
    return found


def verify_tree(bundle: Path, found: set[str]) -> None:
    actual: set[str] = set()
    allowed_directories = {
        parent.as_posix() for name in found for parent in Path(name).parents if parent != Path(".")
    }
    for path in bundle.rglob("*"):
        safe_path(path)
        name = path.relative_to(bundle).as_posix()
        if path.is_file():
            if name not in found | {"manifest.json", SIGNATURE_FILE}:
                raise BackupError("Backup contains an unlisted file.")
            actual.add(name)
        elif not path.is_dir() or name not in allowed_directories:
            raise BackupError("Unexpected backup directory or special file.")
    expected = found | {"manifest.json"}
    if (bundle / SIGNATURE_FILE).is_file():
        expected.add(SIGNATURE_FILE)
    if actual != expected:
        raise BackupError("Backup contains unlisted or missing files.")


def verify_bundle(
    bundle: Path,
    *,
    authentication: bytes | None = None,
    require_postgres_authentication: bool = False,
) -> dict[str, Any]:
    """Validate the full directory before any restore destination is created."""
    bundle = safe_path(bundle)
    manifest_path = bundle / "manifest.json"
    try:
        with manifest_path.open("rb") as handle:
            manifest_bytes = handle.read(MANIFEST_LIMIT + 1)
        if not manifest_bytes or len(manifest_bytes) > MANIFEST_LIMIT:
            raise BackupError("Invalid backup manifest.")
        manifest = json.loads(manifest_bytes)
    except (ValueError, UnicodeError, RecursionError, OSError) as exc:
        raise BackupError("Invalid backup manifest.") from exc
    if (
        not isinstance(manifest, dict)
        or type(manifest.get("version")) is not int
        or manifest["version"] != 1
    ):
        raise BackupError("Unsupported backup manifest.")
    backend = manifest.get("backend")
    if not isinstance(backend, str) or backend not in DATABASE_FILES:
        raise BackupError("Unknown database format.")
    if backend == "postgres":
        if authentication is not None:
            verify_manifest_signature(bundle, authentication, manifest_bytes)
        elif require_postgres_authentication:
            raise BackupError("PostgreSQL restore requires --authentication-key-file.")
    found = verify_entries(bundle, manifest)
    if DATABASE_FILES[backend] not in found or any(
        name in found for kind, name in DATABASE_FILES.items() if kind != backend
    ):
        raise BackupError("Backup must contain exactly one database of the declared format.")
    if type(manifest.get("includes_env")) is not bool or manifest["includes_env"] != (
        "config/.env" in found
    ):
        raise BackupError("Secret configuration declaration does not match the file list.")
    verify_tree(bundle, found)
    if backend == "sqlite":
        check_sqlite(bundle / DATABASE_FILES[backend])
    else:
        with (bundle / DATABASE_FILES[backend]).open("rb") as handle:
            if handle.read(5) != b"PGDMP":
                raise BackupError("PostgreSQL backup is not a custom-format dump.")
    return manifest


def restore_files(bundle: Path, output: Path, manifest: dict[str, Any]) -> Path:
    target = new_directory(output)
    for entry in manifest["files"]:
        copy_new(bundle / entry["path"], target / entry["path"])
        if digest(target / entry["path"]) != (entry["size"], entry["sha256"]):
            raise BackupError("Backup changed after verification.")
    return target
