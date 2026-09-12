"""One collection allowance shared by serial initial and revised query passes."""

import asyncio
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from math import isfinite

from ase.domain.research import ResearchMode
from ase.domain.research_capacity import MAX_COLLECTION_ITEMS, MAX_COLLECTION_REQUESTS


@dataclass(frozen=True, slots=True)
class CollectionBudget:
    requests: int
    seconds: float
    per_request_seconds: float
    items: int

    def __post_init__(self) -> None:
        if (
            not 1 <= self.requests <= MAX_COLLECTION_REQUESTS
            or not 1 <= self.items <= MAX_COLLECTION_ITEMS
        ):
            raise ValueError("Invalid collection request or item budget")
        if (
            any(
                not isfinite(value) or value <= 0
                for value in (self.seconds, self.per_request_seconds)
            )
            or self.seconds > 300
            or self.per_request_seconds > 60
        ):
            raise ValueError("Invalid collection deadline")

    @classmethod
    def for_mode(cls, mode: ResearchMode) -> "CollectionBudget":
        if mode == ResearchMode.ADVANCED:
            return cls(requests=32, seconds=240, per_request_seconds=20, items=1000)
        if mode == ResearchMode.DETAILED:
            return cls(requests=24, seconds=180, per_request_seconds=20, items=800)
        return cls(requests=6, seconds=45, per_request_seconds=12, items=200)


class CollectionRunBudget:
    """Run-local accounting, never reusable across independent research runs.

    Construct immediately before the initial collection pass. Time between passes
    consumes this deadline too. Retain only IDs here; returned batches own the data.
    Passes must run serially and request cancellation does not refund admission.
    The optional monotonic clock supports deterministic deadline tests.
    """

    def __init__(
        self, limits: CollectionBudget, *, clock: Callable[[], float] | None = None
    ) -> None:
        self._limits = limits
        self._clock = clock or asyncio.get_running_loop().time
        self._deadline = self._clock() + limits.seconds
        self._requests = 0
        self._retained_ids: set[str] = set()
        self._active = False

    @property
    def limits(self) -> CollectionBudget:
        return self._limits

    @property
    def requests_used(self) -> int:
        return self._requests

    @property
    def retained_count(self) -> int:
        return len(self._retained_ids)

    @property
    def remaining_requests(self) -> int:
        return self._limits.requests - self._requests

    @property
    def remaining_items(self) -> int:
        return self._limits.items - len(self._retained_ids)

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self._deadline - self._clock())

    @contextmanager
    def pass_scope(self) -> Iterator[None]:
        if self._active:
            raise ValueError("Collection passes sharing a run budget must be serial")
        self._active = True
        try:
            yield
        finally:
            self._active = False

    def admit(self) -> float | None:
        """Consume one request before outbound work, returning its remaining deadline."""
        remaining = self.remaining_seconds
        if self.remaining_requests <= 0 or self.remaining_items <= 0 or remaining <= 0:
            return None
        self._requests += 1
        return min(remaining, self._limits.per_request_seconds)

    def retain(self, event_id: str) -> bool:
        """Charge a new eligible ID once across all passes, without replacing originals."""
        if self.remaining_items <= 0 or event_id in self._retained_ids:
            return False
        self._retained_ids.add(event_id)
        return True
