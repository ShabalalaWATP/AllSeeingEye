"""Offline concurrent `/api/events` read benchmark: direct reads against shared reads.

Run: uv run --directory backend python ../scripts/benchmark_event_reads.py

Builds a retained store of about 58,000 events from development test builders and times N
browsers asking for the same bounded geographic snapshot at once, as they do after a
bulk feed update. No provider requests or live application state are involved; only
aggregate counts and timings are printed. Run separately from load tests.
"""

# ruff: noqa: T201
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend/src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend/tests"))

from ase.adapters.store.memory import InMemoryEventStore
from ase.api.schemas_events import EventOut, EventsOut
from ase.application.feeds.shared_reads import SharedReads
from ase.application.ports.feeds import EventQuery
from ase.domain.errors import RateLimited
from ase.domain.events import Category, Point, freeze_attributes
from feeds_helpers import make_event

CLIENTS = (1, 4, 8, 10)
QUERY = EventQuery(limit=2000, sampling="geographic")


def build_store() -> InMemoryEventStore:
    store = InMemoryEventStore()
    rows = []
    for source, category, count in [
        ("firms_viirs_noaa20", Category.DISASTER, 12000),
        ("aisstream", Category.MARITIME, 20000),
        ("adsb", Category.AVIATION, 12000),
        ("celestrak", Category.SPACE, 16000),
    ]:
        for i in range(count):
            rows.append(
                make_event(
                    str(i),
                    source_id=source,
                    category=category,
                    point=Point((i * 137.5) % 360 - 180, (i * 0.73) % 170 - 85),
                ).with_changes(
                    attributes=freeze_attributes({f"field_{k}": f"value-{i}-{k}" for k in range(8)})
                )
            )
    store.upsert(rows)
    return store


async def run(store: InMemoryEventStore, clients: int, shared: bool) -> dict[str, float | int]:
    builds = 0

    def project(events: list) -> EventsOut:
        nonlocal builds
        builds += 1
        items = [EventOut.from_event(event) for event in events]
        return EventsOut(items=items, count=len(items))

    reads: SharedReads[EventsOut] = SharedReads()

    async def one(index: int) -> bool:
        actor = f"user:{index}"

        async def load() -> EventsOut:
            return await store.read_cooperatively(QUERY, project, admission_key=actor)

        try:
            if shared:
                await reads.read((QUERY, store.generation), load, actor=actor)
            else:
                await load()
        except RateLimited:
            return False
        return True

    start = time.perf_counter()
    served = await asyncio.gather(*(one(index) for index in range(clients)))
    return {
        "total_ms": round((time.perf_counter() - start) * 1000, 1),
        "builds": builds,
        "served": sum(served),
        "rate_limited": clients - sum(served),
    }


async def main() -> None:
    store = build_store()
    await run(store, 1, shared=False)  # Warm the worker thread and parsers.
    out: dict[str, dict[str, dict[str, float | int]]] = {"direct": {}, "shared": {}}
    for clients in CLIENTS:
        out["direct"][str(clients)] = await run(store, clients, shared=False)
        out["shared"][str(clients)] = await run(store, clients, shared=True)
    print(json.dumps({"events": store.stats().total, "clients": out}))


asyncio.run(main())
