"""Shared lifetime limits and conservative usage parsing for report model calls."""

MAX_CALLS = 24
MAX_OUTPUT_TOKENS = 256_000
MAX_COUNTER = 2**31 - 1


def token_count(value: object) -> int | None:
    """Unknown counts stay unknown; bools, negative and oversized values are invalid."""
    return value if type(value) is int and 0 <= value <= MAX_COUNTER else None
