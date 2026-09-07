"""Atomic local reference catalogue ingestion, separate from the live event store."""

import hashlib
import json
import os
import sqlite3
import stat
import tempfile
from contextlib import closing
from pathlib import Path

from ase.adapters.research_records.aiddata_records import (
    MAX_PROJECT_BYTES,
    RELEASE_COMMIT,
    RELEASE_ID,
    parse_project,
)
from ase.domain.evidence_geometry import geometry_to_dict
from ase.domain.project import project_to_dict

MAX_PROJECTS = 10_000
MAX_SOURCE_BYTES = 2 * 1024 * 1024 * 1024
MAX_CATALOGUE_BYTES = 3 * 1024 * 1024 * 1024


def import_project_directory(source_dir: Path, cache_dir: Path) -> Path:
    """Import native project files from the pinned release, without following symlinks.

    An imported subset is allowed and its count is explicit. Source authenticity
    is not inferred from filenames or a supplied release label.
    """
    root = source_dir.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Select a directory of native project GeoJSON files")
    cache_dir.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".aiddata-", suffix=".sqlite", dir=cache_dir)
    os.close(descriptor)
    staging = Path(temporary)
    try:
        digest = _build_catalogue(root, staging)
        if staging.stat().st_size > MAX_CATALOGUE_BYTES:
            raise ValueError("Project catalogue exceeds its disk budget")
        # Flush before atomically creating an immutable name. Existing versions are never replaced.
        with staging.open("r+b") as output:
            os.fsync(output.fileno())
        target = cache_dir / f"aiddata-{RELEASE_ID}-{digest}.sqlite"
        os.link(staging, target)
        return target
    finally:
        staging.unlink(missing_ok=True)


def _build_catalogue(root: Path, staging: Path) -> str:
    count = 0
    total_bytes = 0
    entries: list[str] = []
    with closing(sqlite3.connect(staging)) as connection, connection:
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute(
            "CREATE TABLE projects (id TEXT PRIMARY KEY, recipient_iso3 TEXT NOT NULL, "
            "commitment_year INTEGER, search_text TEXT NOT NULL, record_json TEXT NOT NULL)"
        )
        with os.scandir(root) as files:
            for entry in files:
                if not entry.name.endswith(".geojson"):
                    continue
                if not entry.is_file(follow_symlinks=False):
                    raise ValueError("Project input must be a regular file")
                path = Path(entry.path)
                if path.resolve(strict=True).parent != root:
                    raise ValueError("Project file escapes the selected directory")
                count += 1
                if count > MAX_PROJECTS:
                    raise ValueError("Project catalogue exceeds 10,000 files")
                data = _read_project(path)
                total_bytes += len(data)
                if total_bytes > MAX_SOURCE_BYTES:
                    raise ValueError("Project source data exceeds the import budget")
                record = parse_project(data, expected_id=path.stem)
                payload = {
                    "title": record.title,
                    "recipient": record.recipient,
                    "sector": record.sector,
                    "amount_constant_usd_2021": record.amount_constant_usd_2021,
                    "project": project_to_dict(record.project),
                    "geometry": geometry_to_dict(record.geometry) if record.geometry else None,
                }
                text = " ".join((record.title, record.recipient, record.sector)).casefold()
                connection.execute(
                    "INSERT INTO projects VALUES (?, ?, ?, ?, ?)",
                    (
                        record.project.project_id,
                        record.project.recipient_iso3,
                        record.project.commitment_year,
                        text,
                        json.dumps(payload, ensure_ascii=False, allow_nan=False),
                    ),
                )
                entries.append(f"{record.project.project_id}:{record.project.source_sha256}")
                if staging.stat().st_size > MAX_CATALOGUE_BYTES:
                    raise ValueError("Project catalogue exceeds its disk budget")
        if count == 0:
            raise ValueError("No native project files were found")
        digest = hashlib.sha256("\n".join(sorted(entries)).encode()).hexdigest()
        metadata = {
            "schema_version": "1",
            "release_id": RELEASE_ID,
            "release_commit": RELEASE_COMMIT,
            "project_count": str(count),
            "source_bytes": str(total_bytes),
            "manifest_sha256": digest,
            "authenticity": "Operator-supplied files; source authenticity unverified",
        }
        connection.executemany("INSERT INTO metadata VALUES (?, ?)", metadata.items())
        connection.execute("CREATE INDEX projects_country ON projects(recipient_iso3)")
        connection.execute("CREATE INDEX projects_year ON projects(commitment_year)")
    return digest


def _read_project(path: Path) -> bytes:
    expected = os.stat(path, follow_symlinks=False)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if not stat.S_ISREG(expected.st_mode) or getattr(expected, "st_file_attributes", 0) & reparse:
        raise ValueError("Project input must be a regular non-reparse file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as source:
        opened = os.fstat(source.fileno())
        if (
            not stat.S_ISREG(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino)
            or getattr(opened, "st_file_attributes", 0) & reparse
        ):
            raise ValueError("Project input changed during import")
        return source.read(MAX_PROJECT_BYTES + 1)
