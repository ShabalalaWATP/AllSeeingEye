"""Isolated, real-time native-feed queue audit with no model or database connection.

Run with ``python -m ase.container.native_feed_audit --output PATH``. The default
observation lasts 24 hours. ``--once`` records a smoke check and cannot satisfy it.
Only aggregates reach disk. The ordinary guarded client, parser, bounded store and
translation queue run locally; a sentinel fails on any unexpected model attempt.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections.abc import Sequence
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path
from typing import Any

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.feeds.roster_probe import RosterProbe
from ase.adapters.feeds.rss_seeds import NATIVE_SEEDS, RssSeed
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.budgets import RetentionBudget
from ase.application.translate.queue import BATCH, CALLS_PER_HOUR, TranslationQueue
from ase.domain.events import Category
from ase.infrastructure.clock import SystemClock

DAY_SECONDS = 24 * 60 * 60
MAX_IDENTITIES = 50_000


class NoAutomaticTranslation:
    """An audit tripwire, never a model adapter or simulated translation service."""

    def __init__(self) -> None:
        self.attempts = 0

    async def translate(self, items: Sequence[tuple[str, str]]) -> list[str | None]:
        self.attempts += 1
        raise RuntimeError("Native feeds unexpectedly entered automatic translation.")


class NativeFeedAudit:
    def __init__(self, seeds: Sequence[RssSeed] = NATIVE_SEEDS) -> None:
        if not seeds or len(seeds) > 20 or any(not s.options.translate_on_demand for s in seeds):
            raise ValueError("Audit requires 1 to 20 explicitly on-demand native seeds.")
        self.seeds = tuple(seeds)
        self.clock = SystemClock()
        self.probe = RosterProbe(self.clock, self.seeds)
        self.store = InMemoryEventStore(
            {Category.NEWS: RetentionBudget(timedelta(hours=24), 5_000)},
            memory_budget_bytes=16 * 1024 * 1024,
        )
        self.translator = NoAutomaticTranslation()
        self.queue = TranslationQueue(self.store, InMemoryEventBus(), self.translator, self.clock)
        self.started_at = self.clock.now()
        self.started = time.monotonic()
        self.interval = max(1_800.0, *(s.spec.poll_interval.total_seconds() for s in seeds))
        self.identities: set[str] = set()
        self.identity_capacity_reached = False
        self.rounds = 0
        self.failures = 0
        self.max_round_gap_seconds = 0.0
        self.last_round: float | None = None
        self.observations: list[dict[str, Any]] = []
        self.successful_sources: set[str] = set()
        self.deferred_observations = 0

    async def sample(self) -> None:
        now = time.monotonic()
        if self.last_round is not None:
            self.max_round_gap_seconds = max(self.max_round_gap_seconds, now - self.last_round)
        self.last_round = now
        for seed in self.seeds:
            result, events = await self.probe.fetch(seed)
            row = asdict(result)
            row["round"] = self.rounds
            self.observations.append(row)
            if result.error or result.http_status not in (200, 304):
                self.failures += 1
            if events:
                self.successful_sources.add(seed.spec.id)
            for event in events:
                if event.id not in self.identities:
                    if len(self.identities) == MAX_IDENTITIES:
                        self.identity_capacity_reached = True
                    else:
                        self.identities.add(event.id)
                if "translate_on_demand" in event.tags:
                    self.deferred_observations += 1
            self.store.upsert(events)
        self.store.prune(self.clock.now())
        await self.queue.run_once()
        self.rounds += 1

    def report(self, *, finished: bool) -> dict[str, Any]:
        elapsed = time.monotonic() - self.started
        complete = (
            finished
            and elapsed >= DAY_SECONDS
            and self.rounds >= 1 + int(DAY_SECONDS / self.interval)
            and self.max_round_gap_seconds <= self.interval + 60
            and self.failures == 0
            and len(self.successful_sources) == len(self.seeds)
            and not self.identity_capacity_reached
            and self.translator.attempts == 0
        )
        return {
            "scope": "isolated_native_feed_queue_only",
            "started_at": self.started_at,
            "updated_at": self.clock.now(),
            "elapsed_seconds": round(elapsed, 3),
            "completed_24_hours": complete,
            "rounds": self.rounds,
            "poll_interval_seconds": self.interval,
            "max_round_gap_seconds": round(self.max_round_gap_seconds, 3),
            "distinct_item_ids": len(self.identities),
            "identity_capacity_reached": self.identity_capacity_reached,
            "on_demand_item_observations": self.deferred_observations,
            "feed_failures": self.failures,
            "unexpected_automatic_translation_attempts": self.translator.attempts,
            "configured_hourly_call_limit": CALLS_PER_HOUR,
            "configured_batch_limit": BATCH,
            "observations": self.observations,
            "limitations": "No installed application or model usage was measured. "
            "Repeated feed observations are not unique arrivals. Other feeds and model latency "
            "are outside this audit. Original titles, URLs of articles and bodies are not saved.",
        }

    async def aclose(self) -> None:
        await self.probe.aclose()


def write_report(output: Path, report: dict[str, Any]) -> None:
    """Replace only the report reserved by this process; do not overwrite a stale temp file."""
    temporary = output.with_name(output.name + ".tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, default=str, indent=2) + "\n")
    temporary.replace(output)


async def observe(output: Path, *, once: bool) -> None:
    # Exclusive creation refuses existing files and symlinks, including another audit's report.
    with output.open("x", encoding="utf-8"):
        pass
    audit = NativeFeedAudit()
    finished = False
    deadline = audit.started + (0 if once else DAY_SECONDS)
    try:
        while True:
            await audit.sample()
            write_report(output, audit.report(finished=False))
            if time.monotonic() >= deadline:
                finished = True
                break
            due = min((audit.last_round or audit.started) + audit.interval, deadline)
            while time.monotonic() < due:
                await asyncio.sleep(min(60, due - time.monotonic()))
    finally:
        try:
            write_report(output, audit.report(finished=finished))
        finally:
            await audit.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New aggregate JSON report path")
    parser.add_argument(
        "--once", action="store_true", help="One live probe round, not 24-hour evidence"
    )
    args = parser.parse_args()
    asyncio.run(observe(args.output, once=args.once))


if __name__ == "__main__":
    main()
