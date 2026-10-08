"""One tolerant ISO 8601 reader for upstream timestamps.

Upstream values are untrusted. `datetime.fromisoformat` raises ValueError for
malformed text, and converting an extreme but valid value such as
`0001-01-01T00:00:00+05:00` to UTC raises OverflowError. Either must cost one
item its timestamp, never abort the whole poll.
"""

from __future__ import annotations

from datetime import UTC, datetime

MAX_TIMESTAMP_LENGTH = 64


def parse_utc(value: object) -> datetime | None:
    """An aware UTC datetime, treating naive values as UTC; None when unusable."""
    if not isinstance(value, str) or not value or len(value) > MAX_TIMESTAMP_LENGTH:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)
    except (ValueError, OverflowError):
        return None
