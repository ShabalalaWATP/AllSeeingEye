"""Measure live-store expiry without network access or timing assertions.

From backend: uv run python benchmarks/bench_event_store.py
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from statistics import median
from time import perf_counter

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.budgets import RetentionBudget
from ase.domain.events import Category, Event, Reliability

NOW = datetime(2026, 9, 6, tzinfo=UTC)


def measure(count: int, repeats: int) -> float:
    events = [
        Event(
            id=str(index),
            source_id="benchmark",
            category=Category.NEWS,
            subtype="headline",
            title="Benchmark headline",
            published_at=NOW,
            observed_at=NOW - timedelta(days=10 if index < count // 2 else 0),
            reliability=Reliability.C,
        )
        for index in range(count)
    ]
    durations: list[float] = []
    for _ in range(repeats):
        store = InMemoryEventStore(
            budgets={Category.NEWS: RetentionBudget(timedelta(days=7), count)}
        )
        store.upsert(events)
        started = perf_counter()
        result = store.prune(NOW)
        durations.append((perf_counter() - started) * 1000)
        if result.expired != count // 2 or store.stats().total != count - count // 2:
            raise RuntimeError("Prune returned an unexpected result")
    return median(durations)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", nargs="+", type=int, default=[2000, 6000, 12000])
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1 or any(count < 1 for count in args.counts):
        parser.error("counts and repeats must be positive")
    for count in args.counts:
        print(  # noqa: T201 - this command reports benchmark measurements on stdout.
            f"{count} events, half expired: median {measure(count, args.repeats):.2f} ms"
        )


if __name__ == "__main__":
    main()
