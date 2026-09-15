"""Bounded JSON and strict round-trip checks for explicitly selected frozen records."""

import json
from dataclasses import asdict, fields, is_dataclass
from datetime import date, datetime
from enum import Enum
from functools import lru_cache
from math import isfinite
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter

from ase.domain.report_jobs import canonical_job_payload

MAX_SNAPSHOT_BYTES = 768 * 1024
_PRIVATE_KEYS = frozenset(
    {
        "research_input_id",
        "input_id",
        "preview",
        "image",
        "images",
        "png",
        "raw_bytes",
        "credentials",
        "api_key_hint",
        "base_url",
        "actor",
        "profile",
        "_settings",
        "secret_cipher",
        "session_id",
        "security_version",
    }
)


def encoded(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    )


def json_copy(value: Any) -> Any:
    """Normalise only data emitted by the existing explicit record codecs."""
    return json.loads(encoded(value))


def boundary(value: Any, keys: set[str]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise ValueError("Invalid report snapshot fields")
    # The outer job checkpoint remains schema 1. Inner frozen inputs can evolve
    # independently, while sharing the checkpoint's JSON and size safeguards.
    raw = canonical_job_payload({"schema_version": 1, "snapshot": value})
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Report snapshot exceeds its size budget")
    pending: list[Any] = [value]
    while pending:
        current = pending.pop()
        if type(current) is dict:
            if any(key.casefold() in _PRIVATE_KEYS for key in current):
                raise ValueError("Private capabilities cannot be saved in report snapshots")
            pending.extend(current.values())
        elif type(current) is list:
            pending.extend(current)
        elif type(current) is tuple:
            raise ValueError("Report snapshots require JSON arrays")
    return value


def canonical(original: Any, restored: Any) -> None:
    """Historical codecs are tolerant; queued jobs must never drop or coerce fields."""
    if encoded(original) != encoded(restored):
        raise ValueError("Invalid or non-canonical report snapshot record")


def _scalar(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Report snapshot dates must be timezone aware")
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError("Unsupported frozen record value")


@lru_cache(maxsize=32)
def _adapter(kind: type[Any]) -> TypeAdapter[Any]:
    return TypeAdapter(kind)


def record[T](value: T) -> T:
    """Validate a selected domain record, never an actor, profile, event or whole Job."""
    if not is_dataclass(value) or isinstance(value, type):
        raise ValueError("Expected a frozen domain record")
    # Walk dates before the typed JSON validation, which otherwise accepts naive dates.
    pending: list[Any] = [value]
    while pending:
        current = pending.pop()
        if isinstance(current, datetime):
            _scalar(current)
        elif is_dataclass(current) and not isinstance(current, type):
            pending.extend(getattr(current, field.name) for field in fields(current))
        elif isinstance(current, dict):
            pending.extend(current.values())
        elif isinstance(current, tuple | list):
            pending.extend(current)
    _adapter(type(value)).validate_json(
        json.dumps(asdict(value), default=_scalar, allow_nan=False), strict=True
    )
    return value


def count(value: Any, maximum: int = 2**31 - 1) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError("Invalid report snapshot count")
    return value


def number(value: Any, minimum: float, maximum: float) -> float:
    if type(value) not in (int, float) or not isfinite(value) or not minimum <= value <= maximum:
        raise ValueError("Invalid report snapshot number")
    return float(value)


def text(value: Any, maximum: int, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if type(value) is not str or len(value) > maximum:
        raise ValueError("Invalid report snapshot text")
    return value


def timestamp(value: Any) -> datetime:
    text(value, 64)
    result = datetime.fromisoformat(value)
    _scalar(result)
    return result


def identifier(value: Any) -> UUID | None:
    if value is None:
        return None
    if type(value) is not str or len(value) != 36:
        raise ValueError("Invalid report snapshot identifier")
    result = UUID(value)
    if str(result) != value:
        raise ValueError("Invalid report snapshot identifier")
    return result
