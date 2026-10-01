"""Identical concurrent `/api/events` reads share one selection and response build.

Each retained store has its own shared reads, held weakly so a replaced container (as
in tests) never sees another store's results. Like the stream encoder, this is
public-data sharing only: every caller is authenticated, recorded as a map interest
and checked by its release fence before it receives the shared result.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from weakref import WeakKeyDictionary

from ase.api.schemas_events import EventsOut
from ase.application.feeds.shared_reads import SharedReads
from ase.application.ports.feeds import EventQuery
from ase.application.ports.store_generation import GenerationalEventStore

_READS: WeakKeyDictionary[GenerationalEventStore, SharedReads[EventsOut]] = WeakKeyDictionary()


def shared_reads(store: GenerationalEventStore) -> SharedReads[EventsOut]:
    reads = _READS.get(store)
    if reads is None:
        reads = _READS[store] = SharedReads()
    return reads


async def read_events(
    store: object, query: EventQuery, load: Callable[[], Awaitable[EventsOut]], *, actor: str
) -> EventsOut:
    """Load once per normalised query and store generation; other stores load directly."""
    if not isinstance(store, GenerationalEventStore):
        return await load()
    generation = store.generation
    return await shared_reads(store).read(
        (query, generation),
        load,
        actor=actor,
        current=lambda: store.generation == generation,
    )
