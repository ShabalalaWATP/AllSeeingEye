"""Defensive scalar parsing shared by structured conflict providers."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from urllib.parse import urlsplit

from ase.domain.events import Point


def text(value: object, limit: int = 500) -> str:
    return str(value).strip()[:limit] if isinstance(value, (str, int, float)) else ""


def integer(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(str(value))
        return int(number) if math.isfinite(number) and number.is_integer() else None
    except (ValueError, OverflowError):
        return None


def count(value: object) -> int | None:
    number = integer(value)
    return number if number is not None and 0 <= number <= 1_000_000_000 else None


def when(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)
    except (ValueError, OverflowError):
        return None


def point(latitude: object, longitude: object) -> Point | None:
    try:
        return Point(lat=float(str(latitude)), lon=float(str(longitude)))
    except (ValueError, OverflowError):
        return None


def public_link(value: object) -> str | None:
    candidate = text(value, 2000)
    try:
        parsed = urlsplit(candidate)
        if (
            parsed.scheme in {"https", "http"}
            and parsed.hostname
            and not (parsed.username or parsed.password)
        ):
            return candidate
    except ValueError:
        pass
    return None
