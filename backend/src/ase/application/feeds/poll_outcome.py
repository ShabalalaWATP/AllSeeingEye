"""The result shared by scheduled polls and source administration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PollOutcome:
    source_id: str
    ok: bool
    fetched: int = 0
    changed: int = 0
    error: str | None = None
