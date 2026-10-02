"""Admitted pure projections over one retained snapshot, never live store iteration."""

from collections.abc import Callable

from ase.application.ports.cooperative_feeds import (
    CooperativeEventReader,
    CooperativeSnapshotReader,
)
from ase.application.ports.feeds import EventQuery, EventQueryReader
from ase.domain.events import Event


async def read_board[T](
    store: EventQueryReader, project: Callable[[EventQueryReader], T], *, admission_key: str
) -> T:
    if isinstance(store, CooperativeSnapshotReader):
        return await store.read_snapshot_cooperatively(project, admission_key=admission_key)
    # Small test/alternate readers retain the pure synchronous contract.
    return project(store)


async def read_events[T](
    store: EventQueryReader,
    query: EventQuery,
    project: Callable[[list[Event]], T],
    *,
    admission_key: str,
) -> T:
    if isinstance(store, CooperativeEventReader):
        return await store.read_cooperatively(query, project, admission_key=admission_key)
    return project(store.query(query))
