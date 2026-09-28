"""Offline representative sensor benchmark.

Run: uv run --directory backend python ../scripts/benchmark_backend.py.

Uses development test builders, no provider requests or live application state.
Only aggregate counts and timings are printed. Run separately from load tests.
"""

# ruff: noqa: E402, T201
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend/src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend/tests"))
from dataclasses import replace

from ase.adapters.feeds.firms import SPEC
from ase.adapters.geo.countries import CountryIndex
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.geo import CountryStage
from ase.application.feeds.grading import GradingService, profiles_from_specs
from ase.application.feeds.pipeline import Normaliser, Pipeline
from ase.application.ports.feeds import EventQuery
from ase.domain.events import Category, Point, freeze_attributes
from feeds_helpers import NOW, FakeClock, make_event

rows = []
for source, category, count in [
    ("firms_viirs_noaa20", Category.DISASTER, 10000),
    ("firms_viirs_noaa21", Category.DISASTER, 10000),
    ("aisstream", Category.MARITIME, 20000),
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
                attributes=freeze_attributes({f"field_{k}": f"reported-{i}-{k}" for k in range(12)})
            )
        )
store = InMemoryEventStore()
timings = {}


def measured(label, fn):
    t = time.perf_counter()
    value = fn()
    timings[label] = round((time.perf_counter() - t) * 1000, 2)
    return value


measured("upsert_56k", lambda: store.upsert(rows))
measured("stats", store.stats)
measured("query_geographic_5k", lambda: store.query(EventQuery(limit=5000, sampling="geographic")))
measured("prune", lambda: store.prune(NOW))
pipeline = Pipeline([Normaliser(), CountryStage(CountryIndex.from_resource())])
measured("pipeline_20k", lambda: pipeline.run(rows[:20000]))
profiles = profiles_from_specs([replace(SPEC, id=s) for s in {r.source_id for r in rows}])
grader = GradingService(store, profiles, FakeClock(NOW))
measured("regrade_20k", lambda: grader.regrade(rows[:20000]))
print(
    json.dumps(
        {
            "timings_ms": timings,
            "count": store.stats().total,
            "estimated_MiB": round(store.stats().estimated_bytes / 1048576, 1),
        }
    )
)


import asyncio
import contextlib
from datetime import timedelta

from ase.adapters.geo.public_figures import load_public_figures
from ase.api.schemas_events import EventOut
from ase.application.public_figures import PublicFigureService


def figure_news(count=3000):
    """Retained news of about 450 characters, a few naming office-holders."""
    names = [f.name for f in load_public_figures().figures]
    words = ["officials", "said", "talks", "while", "envoys", "met", "near", "the", "border"]
    news = InMemoryEventStore()
    news.upsert(
        [
            make_event(
                f"n{i}",
                category=Category.NEWS,
                subtype="news_report",
                title=f"{names[i % len(names)] if i % 10 == 0 else 'Envoys'} {' '.join(words)}",
                summary=" ".join(words[(i + k) % len(words)] for k in range(70))[:370],
                published_at=NOW - timedelta(minutes=i),
                point=None,
            )
            for i in range(count)
        ]
    )
    return news


async def tracked(label, action):
    samples = []

    async def heartbeat():
        before = time.perf_counter()
        while True:
            await asyncio.sleep(0.001)
            current = time.perf_counter()
            samples.append((current - before) * 1000)
            before = current

    monitor = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.005)
    start = time.perf_counter()
    await action()
    elapsed = (time.perf_counter() - start) * 1000
    await asyncio.sleep(0.005)
    monitor.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await monitor
    return {"total_ms": round(elapsed, 2), "max_loop_gap_ms": round(max(samples), 2)}


async def main():
    async def sync_grade():
        grader.regrade(rows[:20000])

    async def sync_query():
        return [
            EventOut.from_event(e)
            for e in store.query(EventQuery(limit=2000, sampling="geographic"))
        ]

    out = {}
    out["sync_regrade"] = await tracked("sync_grade", sync_grade)
    out["cooperative_regrade"] = await tracked(
        "grade", lambda: grader.regrade_cooperatively(rows[:20000])
    )
    out["sync_query_and_dto"] = await tracked("syncquery", sync_query)
    out["worker_query_and_dto"] = await tracked(
        "query",
        lambda: store.read_cooperatively(
            EventQuery(limit=2000, sampling="geographic"),
            lambda events: [EventOut.from_event(e) for e in events],
        ),
    )
    fresh = InMemoryEventStore()
    out["cooperative_upsert"] = await tracked("upsert", lambda: fresh.upsert_cooperatively(rows))
    figures = PublicFigureService(figure_news(), FakeClock(NOW), load_public_figures())
    out["worker_figures_board_3k"] = await tracked(
        "figures", lambda: figures.board(admission_key="benchmark")
    )
    print(json.dumps(out))


asyncio.run(main())
