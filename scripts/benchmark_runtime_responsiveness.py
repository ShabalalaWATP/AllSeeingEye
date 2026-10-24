"""Offline social, aviation and translation responsiveness probe (KAN-248/249).

Run serially with the chosen checkout's backend venv and no coverage. --checkout
selects its source/tests, so this identical fixture can measure base and candidate.
All 60,000 events are synthetic and within the normal store bounds. No provider,
model, operator database or production endpoint is used. The busy-hour fixture
is a high-load scenario, not an observation of production occupancy. Windows
timer granularity contributes to loop gaps, so compare the idle control too.
"""

# ruff: noqa: E402, T201

import argparse
import asyncio
import contextlib
import gc
import inspect
import json
import statistics
import sys
import time
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--checkout", type=Path, default=Path(__file__).resolve().parents[1])
parser.add_argument("--skip-worker", action="store_true")
args = parser.parse_args()
ROOT = args.checkout.resolve()
sys.path[:0] = [str(ROOT / "backend/src"), str(ROOT / "backend/tests")]

from ase.adapters.store.memory import InMemoryEventStore
from ase.api.schemas_events import EventOut
from ase.application.ports.feeds import EventQuery
from ase.application.trackers.aviation import AviationService, WatchedArea
from ase.application.trackers.social import SocialService
from ase.application.translate.queue import TranslationQueue
from ase.domain.aviation import JamMap
from ase.domain.events import Category, Point, freeze_attributes
from ase.domain.social import WatchedTerm, keyword_counts
from feeds_helpers import NOW, FakeClock, make_event

if not Path(sys.modules["ase"].__file__).resolve().is_relative_to(ROOT / "backend/src"):
    raise RuntimeError("Probe imported application code outside the selected checkout")


def build_store():
    store = InMemoryEventStore()
    for category, count in (
        (Category.SOCIAL, 10000),
        (Category.AVIATION, 15000),
        (Category.NEWS, 20000),
        (Category.MARITIME, 15000),
    ):
        records = []
        for i in range(count):
            tags = (
                ("bluesky",)
                if category is Category.SOCIAL
                else (f"area_{i % 22}", "military" if i % 3 == 0 else "civilian")
            )
            records.append(
                make_event(
                    f"{category.value}-{i}",
                    source_id=f"probe_{category.value}",
                    category=category,
                    subtype={
                        Category.SOCIAL: "post",
                        Category.AVIATION: "aircraft",
                        Category.NEWS: "news_report",
                        Category.MARITIME: "vessel",
                    }[category],
                    title=f"Officials discuss watch phrase {i % 32} and shipping #update",
                    summary=(
                        "Local officials reported economic developments "
                        "and international shipping. " * 7
                    ),
                    point=Point((i * 137.5) % 360 - 180, (i * 0.73) % 170 - 85),
                    country_iso="GB",
                    published_at=(
                        NOW - timedelta(seconds=i % 300)
                        if category is Category.AVIATION
                        else NOW - timedelta(minutes=30)
                    ),
                    observed_at=NOW - timedelta(seconds=i % 300),
                ).with_changes(
                    language="en",
                    tags=frozenset(tags),
                    attributes=freeze_attributes(
                        {f"field_{k}": f"value-{i}-{k}" for k in range(8)}
                    ),
                )
            )
        store.upsert(records)
    store.prune(NOW)
    return store


async def tracked(action):
    gaps, collections, starts = [], [], {}

    def collected(phase, info):
        if phase == "start":
            starts[info["generation"]] = time.perf_counter()
        else:
            start = starts.pop(info["generation"], None)
            if start is not None:
                collections.append((info["generation"], (time.perf_counter() - start) * 1000))

    async def heartbeat():
        previous = time.perf_counter()
        while True:
            await asyncio.sleep(0.001)
            current = time.perf_counter()
            gaps.append((current - previous) * 1000)
            previous = current

    task = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.005)
    gc.callbacks.append(collected)
    start = time.perf_counter()
    try:
        result = await action()
        elapsed = (time.perf_counter() - start) * 1000
        await asyncio.sleep(0.005)
    finally:
        gc.callbacks.remove(collected)
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    return {
        "ms": elapsed,
        "max_loop_gap_ms": max(gaps, default=0),
        "gc_max_ms": max((item[1] for item in collections), default=0),
        "gc_gen2_count": sum(item[0] == 2 for item in collections),
        "result_count": result if isinstance(result, int) else None,
    }


async def rounds(label, action, count=5):
    await action()
    samples = [await tracked(action) for _ in range(count)]
    result = {
        "probe": label,
        "rounds": count,
        "median_ms": round(statistics.median(s["ms"] for s in samples), 3),
        "max_ms": round(max(s["ms"] for s in samples), 3),
        "median_max_loop_gap_ms": round(
            statistics.median(s["max_loop_gap_ms"] for s in samples), 3
        ),
        "worst_loop_gap_ms": round(max(s["max_loop_gap_ms"] for s in samples), 3),
        "worst_gc_ms": round(max(s["gc_max_ms"] for s in samples), 3),
        "gc_gen2_count": sum(s["gc_gen2_count"] for s in samples),
        "samples": [
            {k: round(v, 3) if isinstance(v, float) else v for k, v in s.items()} for s in samples
        ],
    }
    print(json.dumps(result), flush=True)


async def main():
    store = build_store()
    stats = store.stats()
    print(
        json.dumps(
            {
                "fixture_records": stats.total,
                "source_package": str(Path(sys.modules["ase"].__file__).resolve()),
                "estimated_MiB": round(stats.estimated_bytes / 1048576, 2),
                "social": 10000,
                "aviation": 15000,
                "terms": 32,
                "areas": 22,
            }
        ),
        flush=True,
    )
    if stats.total != 60000:
        raise RuntimeError("Unexpected fixture retention")
    clock = FakeClock(NOW)
    actor = SimpleNamespace(id=uuid4())
    terms = tuple(
        WatchedTerm(
            f"watch phrase {i}",
            i < 16,
            frozenset() if i < 16 else frozenset({actor.id}),
        )
        for i in range(32)
    )
    source = SimpleNamespace(visible_to=AsyncMock(return_value=terms))
    activity = SimpleNamespace(baselines=AsyncMock(return_value={}))
    social = SocialService(store, source, activity, clock)
    aviation = AviationService(
        store, JamMap(), clock, tuple(WatchedArea(str(i), str(i)) for i in range(22))
    )
    translator = SimpleNamespace(
        translate=AsyncMock(side_effect=AssertionError("Network forbidden"))
    )
    translation = TranslationQueue(store, SimpleNamespace(publish=AsyncMock()), translator, clock)

    async def aviation_board():
        result = aviation.board({}, {})
        if inspect.isawaitable(result):
            result = await result
        return result.military_total

    async def social_board():
        return (await social.board(actor)).total

    await rounds("idle_timer_control", lambda: asyncio.sleep(0.025))
    await rounds("translation_all_english", translation.run_once)

    # Force a real store generation change before each poll, so an unchanged-store
    # empty-result cache cannot hide the cost of selection while feeds are active.
    seed = store.query(EventQuery(limit=1))[0]

    async def translation_after_feed_change():
        store.put([seed])
        return await translation.run_once()

    await rounds("translation_all_english_after_feed_change", translation_after_feed_change)
    await rounds("aviation_board_15k_22_areas", aviation_board)
    social_rows = store.query(EventQuery(categories=frozenset({Category.SOCIAL}), limit=10000))
    for distribution in ("burst_hour", "uniform_24h"):
        changed = [
            e.with_changes(
                published_at=(
                    NOW - timedelta(minutes=30)
                    if distribution == "burst_hour"
                    else NOW - timedelta(seconds=1 + (i * 86398) // len(social_rows))
                )
            )
            for i, e in enumerate(social_rows)
        ]
        store.put(changed)
        last_hour = [e for e in changed if NOW - timedelta(hours=1) <= e.published_at < NOW]
        for term_count in (16, 32):
            visible_terms = terms[:term_count]
            source.visible_to.return_value = visible_terms
            await rounds(f"social_board_{distribution}_{term_count}_visible_terms", social_board, 3)

            async def keyword_only(last_hour=last_hour, visible_terms=visible_terms):
                return sum(keyword_counts(last_hour, visible_terms).values())

            await rounds(
                f"keyword_only_{distribution}_{len(last_hour)}_posts_{term_count}_terms",
                keyword_only,
                3,
            )
    if args.skip_worker:
        if translator.translate.await_count:
            raise RuntimeError("Offline probe attempted a model call")
        return
    query = EventQuery(limit=2000, sampling="geographic")

    async def query_only():
        return len(await store.read_cooperatively(query, lambda rows: rows, admission_key="probe"))

    async def query_dto():
        return len(
            await store.read_cooperatively(
                query, lambda rows: [EventOut.from_event(e) for e in rows], admission_key="probe"
            )
        )

    await rounds("warm_worker_query_only", query_only, 10)
    await rounds("warm_worker_query_and_dto", query_dto, 10)
    if translator.translate.await_count:
        raise RuntimeError("Offline probe attempted a model call")


if __name__ == "__main__":
    asyncio.run(main())
