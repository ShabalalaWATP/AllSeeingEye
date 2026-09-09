"""Optional asynchronous bulk operations for large in-process sensor batches."""

from collections.abc import Callable, Sequence
from typing import Protocol, runtime_checkable

from ase.application.ports.feeds import EventQuery, UpsertResult
from ase.domain.events import Event


@runtime_checkable
class CooperativeEventStore(Protocol):
    async def upsert_cooperatively(self, events: list[Event]) -> UpsertResult: ...
    async def put_grades_cooperatively(self, events: list[Event]) -> None: ...


@runtime_checkable
class CooperativeGrader(Protocol):
    async def regrade_cooperatively(self, events: Sequence[Event]) -> list[Event]: ...


@runtime_checkable
class CooperativeEventReader(Protocol):
    async def read_cooperatively[T](
        self, query: EventQuery, project: Callable[[list[Event]], T]
    ) -> T: ...
