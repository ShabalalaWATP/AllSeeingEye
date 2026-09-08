"""Bounded, replace-in-place orbital inputs, never a history of map events."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

MAX_OBJECTS = 20_000
MAX_CACHE_BYTES = 12 * 1024 * 1024
ELEMENT_TTL = timedelta(hours=2)
CACHE_IDS = frozenset(
    f"celestrak_{group}" for group in ("stations", "active", "military", "skynet")
)
ORBITAL_FIELDS = frozenset(
    [
        "OBJECT_NAME",
        "OBJECT_ID",
        "EPOCH",
        "MEAN_MOTION",
        "ECCENTRICITY",
        "INCLINATION",
        "RA_OF_ASC_NODE",
        "ARG_OF_PERICENTER",
        "MEAN_ANOMALY",
        "EPHEMERIS_TYPE",
        "CLASSIFICATION_TYPE",
        "NORAD_CAT_ID",
        "ELEMENT_SET_NO",
        "REV_AT_EPOCH",
        "BSTAR",
        "MEAN_MOTION_DOT",
        "MEAN_MOTION_DDOT",
    ]
)


def bounded_rows(data: object) -> list[dict[str, Any]]:
    if not isinstance(data, list) or not data:
        raise ValueError("Satellite catalogue has no orbital records")
    rows = []
    for item in data[:MAX_OBJECTS]:
        if not isinstance(item, dict):
            continue
        row = {
            key: str(value)[:300]
            for key, value in item.items()
            if key in ORBITAL_FIELDS and isinstance(value, (str, int, float))
        }
        # CelesTrak omits a blank international designator for some catalogue objects.
        row.setdefault("OBJECT_ID", "")
        if {"NORAD_CAT_ID", "EPOCH", "MEAN_MOTION"} <= row.keys():
            rows.append(row)
    if not rows:
        raise ValueError("Satellite catalogue is missing orbital fields")
    return rows


@dataclass
class ElementState:
    rows: list[dict[str, Any]] = field(default_factory=list)
    fetched_at: datetime | None = None
    retry_at: datetime | None = None
    error: str | None = None
    blocked: bool = False


def _timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        raise ValueError("Cache timestamp has no timezone")
    return parsed.astimezone(UTC)


class SatelliteCache:
    """One bounded file per built-in source, for a single feed worker per directory."""

    def __init__(self, directory: Path, source_id: str, url: str) -> None:
        if source_id not in CACHE_IDS:
            raise ValueError("Unsupported satellite cache source")
        self.path = directory / f"{source_id}.json"
        self.source_id, self.url = source_id, url

    def load(self, now: datetime) -> ElementState:
        try:
            with self.path.open("rb") as stream:
                raw = stream.read(MAX_CACHE_BYTES + 1)
            if len(raw) > MAX_CACHE_BYTES:
                raise ValueError("Cache too large")
            data = json.loads(raw)
            if (
                data["version"] != 1
                or data["source_id"] != self.source_id
                or data["url"] != self.url
            ):
                raise ValueError("Cache source does not match")
            fetched_at, retry_at = _timestamp(data["fetched_at"]), _timestamp(data["retry_at"])
            if (fetched_at and fetched_at > now) or (retry_at and retry_at > now + ELEMENT_TTL):
                raise ValueError("Cache timestamps are in the future")
            rows = bounded_rows(data["rows"]) if data["rows"] else []
            if rows and fetched_at is None:
                raise ValueError("Cache rows have no download time")
            return ElementState(
                rows,
                fetched_at,
                retry_at,
                str(data["error"])[:300] if data.get("error") else None,
                data.get("blocked") is True,
            )
        except FileNotFoundError:
            return ElementState()
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            # Do not reset the provider's request budget when a recent file is damaged.
            return ElementState(
                retry_at=now + ELEMENT_TTL,
                error="CelesTrak cache unreadable; waiting two hours before downloading",
            )

    def save(self, state: ElementState) -> None:
        data = json.dumps(
            {
                "version": 1,
                "source_id": self.source_id,
                "url": self.url,
                "fetched_at": state.fetched_at.isoformat() if state.fetched_at else None,
                "retry_at": state.retry_at.isoformat() if state.retry_at else None,
                "error": state.error,
                "blocked": state.blocked,
                "rows": state.rows,
            },
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        if len(data) > MAX_CACHE_BYTES:
            raise OSError("Satellite cache exceeds its byte limit")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=self.path.parent, suffix=".tmp", delete=False
            ) as f:
                temporary = f.name
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
