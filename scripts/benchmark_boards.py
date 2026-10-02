"""Offline KAN-35 board/maintenance heartbeat probe, 60,000 retained events.

Run with the chosen checkout's backend venv. --checkout selects its source/tests,
so the identical checked-in fixture can measure the base and changed revisions.
These are controlled measurements, not unit-test deadlines or provider traffic.
"""

# ruff: noqa: PLC0415, T201
import argparse
import asyncio
import contextlib
import json
import sys
import time
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock


def configure():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    sys.path[:0] = [str(args.checkout / "backend/src"), str(args.checkout / "backend/tests")]
    return args


async def tracked(action):
    gaps = []

    async def heartbeat():
        previous = time.perf_counter()
        while True:
            await asyncio.sleep(0.001)
            now = time.perf_counter()
            gaps.append((now - previous) * 1000)
            previous = now

    task = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.005)
    start = time.perf_counter()
    await action()
    elapsed = (time.perf_counter() - start) * 1000
    await asyncio.sleep(0.005)
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    return {"total_ms": round(elapsed, 3), "max_loop_gap_ms": round(max(gaps), 3)}


async def run():
    from ase.adapters.feeds.cisa_kev import SPEC as KEV
    from ase.adapters.feeds.rss_seeds import ECONOMY_SEEDS
    from ase.adapters.geo.conflicts import ConflictIndex
    from ase.adapters.store.memory import InMemoryEventStore
    from ase.application.cyber import CyberService
    from ase.application.economy_news import EconomyNewsService
    from ase.application.feeds.budgets import RetentionBudget
    from ase.application.feeds.health import HealthRegistry
    from ase.application.trackers.boards import TrackerService
    from ase.application.trackers.modules import ModuleService
    from ase.application.ukraine import UkraineBoardService
    from ase.domain.events import Category, Point
    from feeds_helpers import NOW, FakeClock, make_event

    rows = []
    for category, source, subtype in (
        (Category.DISASTER, "usgs_earthquakes", "earthquake"),
        (Category.CONFLICT, "gdelt", "armed_conflict"),
        (Category.MARITIME, "nga_navarea", "navarea_warning"),
        (Category.SPACE, "celestrak_stations", "satellite"),
        (Category.CYBER, KEV.id, "known_exploited_vulnerability"),
        (Category.ECONOMIC, "economic_bbc_business", "news_report"),
    ):
        rows.extend(
            make_event(
                str(i),
                category=category,
                source_id=source,
                subtype=subtype,
                title=f"Ukraine inflation and energy report {i}",
                country_iso="UA",
                point=Point(30 + (i % 80) / 10, 48),
                published_at=NOW
                - timedelta(minutes=i % (5 if category is Category.SPACE else 2000)),
                observed_at=NOW - timedelta(seconds=i % 1000),
            )
            for i in range(10000)
        )
    store = InMemoryEventStore(
        budgets={category: RetentionBudget(timedelta(days=30), 15000) for category in Category}
    )
    store.upsert(rows)
    if store.stats().total != 60000:
        raise RuntimeError("Fixture does not retain all 60,000 events")
    clock = FakeClock(NOW)
    conflicts = ConflictIndex.from_resource()
    trackers = TrackerService(store, conflicts, clock)
    modules = ModuleService(store, clock)
    ukraine = UkraineBoardService(store, clock, conflicts, None)
    switches = SimpleNamespace(
        enabled_many=AsyncMock(side_effect=lambda ids: dict.fromkeys(ids, True))
    )
    cyber = CyberService(store, clock, {KEV.id: KEV}, switches, HealthRegistry())
    economy = EconomyNewsService(
        store, clock, {seed.spec.id: seed.spec for seed in ECONOMY_SEEDS}, switches
    )

    async def board(service, method):
        if hasattr(service, "read"):
            return await service.read(
                lambda reader: getattr(reader, method)(), admission_key="benchmark"
            )
        return getattr(service, method)()

    result = {"fixture_records": 60000}
    for name, service, method in (
        ("disaster", trackers, "disaster_board"),
        ("conflict", trackers, "conflict_board"),
        ("maritime", modules, "maritime_board"),
        ("space", modules, "space_board"),
        ("cyber_tracker", modules, "cyber_board"),
        ("ukraine", ukraine, "board"),
    ):
        result[name] = await tracked(lambda service=service, method=method: board(service, method))
    result["cyber"] = await tracked(cyber.read)
    result["economy"] = await tracked(economy.read)

    async def prune():
        store.prune(NOW)

    result["initial_prune"] = await tracked(prune)
    result["retained_after_prune"] = store.stats().total
    result["steady_prune"] = await tracked(prune)
    bounded = InMemoryEventStore(memory_budget_bytes=store.stats().estimated_bytes)
    bounded.upsert(rows)

    async def overflow():
        bounded.upsert(
            [
                make_event(f"overflow-{i}", observed_at=NOW + timedelta(seconds=1))
                for i in range(250)
            ]
        )

    result["over_budget_upsert_250"] = await tracked(overflow)
    print(json.dumps(result))


if __name__ == "__main__":
    configure()
    asyncio.run(run())
