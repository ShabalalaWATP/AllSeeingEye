"""Shared lifetime limits and conservative usage parsing for report model calls."""

from collections.abc import Mapping, Sequence
from typing import Any

MAX_CALLS = 24
MAX_OUTPUT_TOKENS = 256_000
MAX_COUNTER = 2**31 - 1


def token_count(value: object) -> int | None:
    """Unknown counts stay unknown; bools, negative and oversized values are invalid."""
    return value if type(value) is int and 0 <= value <= MAX_COUNTER else None


NOT_DISPATCHED_ERROR = "not_dispatched"


def released_before_dispatch(call: object) -> bool:
    """A reservation refused before any provider request; it consumed no allowance.

    Such rows stay in the ledger for the settlement fence, but they never count toward
    the lifetime or per-stage call limits, and an explicit resume removes them.
    """
    return (
        isinstance(call, Mapping)
        and call.get("status") == "failed"
        and call.get("error") == NOT_DISPATCHED_ERROR
        and token_count(call.get("prompt_tokens")) == 0
        and token_count(call.get("completion_tokens")) == 0
    )


def dispatched_calls(calls: Sequence[Any]) -> list[Any]:
    """Every call that reached, or may have reached, a provider."""
    return [call for call in calls if not released_before_dispatch(call)]
