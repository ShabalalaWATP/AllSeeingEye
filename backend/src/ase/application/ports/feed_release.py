"""Optional generation-aware publication for reconfigurable feeds."""

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ase.application.ports.feeds import FeedConnector
from ase.domain.events import Event


class FeedUnavailable(Exception):
    """Unconfigured feeds are idle, not circuit-breaker failures."""


@dataclass(frozen=True, slots=True)
class FetchedBatch:
    events: list[Event]
    generation: int


@runtime_checkable
class GuardedFeedConnector(FeedConnector, Protocol):
    async def current_generation(self) -> int: ...
    async def fetch_batch(self) -> FetchedBatch: ...
    def release_guard(self, generation: int) -> AbstractAsyncContextManager[bool]: ...
