"""Explicit local import and atomic immutable publication, never query-triggered downloads."""

import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from ase.adapters.research_records.designation_snapshot import (
    MAX_BYTES,
    MAX_SOURCE_BYTES,
    Authority,
    DesignationRecord,
    DesignationSnapshot,
    parse_csv,
)


def import_designation_csv(
    source_path: Path,
    cache_dir: Path,
    authority: Authority,
    version: str,
    published_at: datetime,
    licence: str,
) -> Path:
    with source_path.open("rb") as source:
        data = source.read(MAX_SOURCE_BYTES + 1)
    snapshot = DesignationSnapshot(
        authority,
        version,
        published_at,
        licence,
        hashlib.sha256(data).hexdigest(),
        parse_csv(data, authority, published_at),
    )
    payload = asdict(snapshot)
    payload["published_at"] = snapshot.published_at.isoformat()
    payload["schema_version"] = 1
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_BYTES:
        raise ValueError("Normalised snapshot exceeds 32 MiB")
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"{authority}-{version}.json"
    # A same-volume hard link creates the final name atomically and fails if the
    # version already exists. No existing file is replaced, even during a race.
    descriptor, temporary = tempfile.mkstemp(prefix=".designation-", dir=cache_dir)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target


def load_designation_snapshot(path: Path) -> DesignationSnapshot:
    with path.open("rb") as source:
        encoded = source.read(MAX_BYTES + 1)
    if len(encoded) > MAX_BYTES:
        raise ValueError("Snapshot exceeds 32 MiB")
    payload = json.loads(encoded)
    if not isinstance(payload, dict) or payload.pop("schema_version", None) != 1:
        raise ValueError("Unsupported designation snapshot schema")
    raw_records = payload.pop("records", None)
    if not isinstance(raw_records, list) or len(raw_records) > 100_000:
        raise ValueError("Invalid designation snapshot records")
    return DesignationSnapshot(
        **{**payload, "published_at": datetime.fromisoformat(payload["published_at"])},
        records=tuple(DesignationRecord(**record) for record in raw_records),
    )
