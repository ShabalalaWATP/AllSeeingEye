"""Restoring and saving the live store: retention, budgets, lifecycle order and settings."""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from ase.adapters.store.memory import InMemoryEventStore, estimate_bytes
from ase.adapters.store.snapshot_file import GzipSnapshotFile
from ase.app_lifecycle import lifespan
from ase.application.feeds.live_snapshot import LiveStoreSnapshots
from ase.application.ports.feeds import EventQuery
from ase.application.ports.live_snapshot import SnapshotLoad
from ase.container.live_snapshot import build_live_snapshot
from ase.domain.events import Category, Event
from ase.infrastructure.settings import Environment, Settings
from feeds_helpers import NOW, FakeClock, make_event

INTERVAL = timedelta(minutes=5)


class RecordingStorage:
    def __init__(self, events: Sequence[Event] = (), order: list[str] | None = None) -> None:
        self.events = tuple(events)
        self.order = order if order is not None else []
        self.saved: list[tuple[list[Event], datetime]] = []
        self.active = self.peak = 0
        self.fail_write = False
        self._lock = threading.Lock()

    def read(self) -> SnapshotLoad:
        self.order.append("read")
        return SnapshotLoad(self.events, skipped=1)

    def write(self, events: Sequence[Event], saved_at: datetime) -> bool:
        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            time.sleep(0.02)
            if self.fail_write:
                raise OSError("disk full")
            self.order.append("write")
            self.saved.append((list(events), saved_at))
            return True
        finally:
            with self._lock:
                self.active -= 1


async def idle(_seconds: float) -> None:
    await asyncio.Event().wait()


def service(store: InMemoryEventStore, storage: object, **options: object) -> LiveStoreSnapshots:
    values: dict[str, object] = {"interval": INTERVAL, "sleep": idle} | options
    return LiveStoreSnapshots(store, storage, FakeClock(NOW), **values)  # type: ignore[arg-type]


def aged(key: str, category: Category, age: timedelta) -> Event:
    return make_event(key, category=category, observed_at=NOW - age, published_at=NOW - age)


async def test_round_trip_restores_retained_events_and_drops_expired(tmp_path: Path) -> None:
    fresh = aged("fresh", Category.NEWS, timedelta(hours=1))
    stale = aged("stale", Category.NEWS, timedelta(hours=80))
    conflict = aged("conflict", Category.CONFLICT, timedelta(days=10))
    flight = aged("flight", Category.AVIATION, timedelta(minutes=20))
    source = InMemoryEventStore()
    source.upsert([fresh, stale, conflict, flight])
    file = GzipSnapshotFile(
        tmp_path / "live.jsonl.gz",
        key=b"k" * 32,
        max_bytes=2**20,
        max_decompressed_bytes=2**22,
        max_events=100,
    )
    assert await service(source, file).save()
    restored = InMemoryEventStore()
    assert await service(restored, file).load() == 2
    assert restored.get(fresh.id) == fresh
    assert restored.get(conflict.id) == conflict
    assert restored.get(stale.id) is None
    assert restored.get(flight.id) is None
    assert restored.query(EventQuery()) == [fresh, conflict]


def test_restored_events_upsert_like_polled_events() -> None:
    event = make_event("a")
    store = InMemoryEventStore()
    assert store.restore([event], NOW) == 1
    again = store.upsert([event])
    assert (again.added, again.updated, again.unchanged) == (0, 0, 1)
    changed = store.upsert([make_event("a", version=2, title="Changed")])
    assert (changed.updated, changed.changed_ids) == (1, (event.id,))
    assert store.prune(NOW).ids == ()


def test_restore_respects_the_memory_budget_and_skips_a_populated_store() -> None:
    events = [make_event(str(age), observed_at=NOW - timedelta(hours=age)) for age in range(5)]
    budget = sum(estimate_bytes(event) for event in events[:2])
    store = InMemoryEventStore(memory_budget_bytes=budget)
    assert store.restore(events, NOW) == 2
    assert {event.id for event in store.retained()} == {events[0].id, events[1].id}
    assert store.restore([make_event("late")], NOW) == 0
    assert store.get(make_event("late").id) is None


async def test_start_loads_once_and_stop_saves_after_a_completed_load() -> None:
    storage = RecordingStorage([make_event("a")])
    store = InMemoryEventStore()
    snapshots = service(store, storage)
    await snapshots.start()
    assert store.get(make_event("a").id) is not None
    assert await snapshots.load() == 0
    await snapshots.stop()
    assert storage.order == ["read", "write"]
    assert [event.id for event in storage.saved[0][0]] == [make_event("a").id]
    assert storage.saved[0][1] == NOW


async def test_stop_without_a_completed_load_keeps_the_previous_file() -> None:
    storage = RecordingStorage()
    await service(InMemoryEventStore(), storage).stop()
    assert storage.order == []


async def test_read_failure_never_blocks_startup() -> None:
    storage = RecordingStorage()
    storage.read = Mock(side_effect=MemoryError("too large"))  # type: ignore[method-assign]
    snapshots = service(InMemoryEventStore(), storage)
    assert await snapshots.load() == 0
    await snapshots.stop()
    assert storage.order == ["write"]


async def test_periodic_saves_follow_the_interval_and_never_overlap() -> None:
    storage = RecordingStorage()
    waits: list[float] = []

    async def sleep(seconds: float) -> None:
        waits.append(seconds)
        if len(waits) > 2:
            await asyncio.Event().wait()

    snapshots = service(InMemoryEventStore(), storage, sleep=sleep)
    await snapshots.start()
    for _ in range(200):
        if len(storage.saved) == 2:
            break
        await asyncio.sleep(0.01)
    await asyncio.gather(snapshots.save(), snapshots.save())
    await snapshots.stop()
    assert waits[0] == INTERVAL.total_seconds()
    assert len(storage.saved) == 5
    assert storage.peak == 1


async def test_failed_save_is_reported_without_raising() -> None:
    storage = RecordingStorage()
    storage.fail_write = True
    assert not await service(InMemoryEventStore(), storage).save()


def make_settings(monkeypatch: pytest.MonkeyPatch, env: Environment, **values: object) -> Settings:
    for name in ("PATH", "INTERVAL_SECONDS", "MAX_MB"):
        monkeypatch.delenv(f"ASE_LIVE_SNAPSHOT_{name}", raising=False)
    return Settings(_env_file=None, env=env, **values)  # type: ignore[call-arg, arg-type]


def test_snapshot_defaults_on_outside_tests_and_empty_disables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    development = make_settings(monkeypatch, Environment.DEV)
    assert development.live_snapshot_file == Path("data/live-store.jsonl.gz")
    assert development.live_snapshot_interval_seconds == 300
    assert development.live_snapshot_max_mb == 128
    assert make_settings(monkeypatch, Environment.TEST).live_snapshot_file is None
    disabled = make_settings(monkeypatch, Environment.DEV, live_snapshot_path=" ")
    assert disabled.live_snapshot_file is None
    opted_in = make_settings(monkeypatch, Environment.TEST, live_snapshot_path="cache/live.gz")
    assert opted_in.live_snapshot_file == Path("cache/live.gz")
    for bad in ({"live_snapshot_interval_seconds": 59}, {"live_snapshot_max_mb": 0}):
        with pytest.raises(ValidationError):
            make_settings(monkeypatch, Environment.TEST, **bad)


def test_container_builds_nothing_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    disabled = SimpleNamespace(settings=make_settings(monkeypatch, Environment.TEST))
    assert build_live_snapshot(disabled) is None  # type: ignore[arg-type]
    enabled = SimpleNamespace(
        settings=make_settings(monkeypatch, Environment.TEST, live_snapshot_path="live.gz"),
        store=InMemoryEventStore(),
        clock=FakeClock(NOW),
    )
    assert isinstance(build_live_snapshot(enabled), LiveStoreSnapshots)  # type: ignore[arg-type]


FEED_WORKERS = ("scheduler", "aviation_monitor", "evaluator", "translation_queue")
OTHER_WORKERS = ("conflict_screening", "social_monitor", "schedule_runner", "report_job_worker")
Lifecycle = tuple[FastAPI, list[str], "RecordingStorage"]


@pytest.fixture
def lifecycle(monkeypatch: pytest.MonkeyPatch) -> Lifecycle:
    order: list[str] = []
    storage = RecordingStorage([make_event("restored")], order)
    store = InMemoryEventStore()

    def worker(name: str) -> SimpleNamespace:
        return SimpleNamespace(
            start=AsyncMock(side_effect=lambda: order.append(f"{name}.start")),
            stop=AsyncMock(side_effect=lambda: order.append(f"{name}.stop")),
        )

    monkeypatch.setattr("ase.app_lifecycle.expire_original_assets", AsyncMock())
    for name in ("alert_dispatcher", "notification_dispatcher", "digest_worker"):
        monkeypatch.setattr(f"ase.app_lifecycle.{name}", lambda _: SimpleNamespace(run=AsyncMock()))
    monkeypatch.setattr("ase.app_lifecycle.run_web_push", AsyncMock())
    monkeypatch.setattr(
        "ase.app_lifecycle.build_annotation_monitor_worker",
        lambda _: SimpleNamespace(run=AsyncMock()),
    )
    monkeypatch.setattr("ase.app_lifecycle.build_live_snapshot", lambda _: service(store, storage))
    app = FastAPI()
    app.state.container = SimpleNamespace(
        settings=SimpleNamespace(feeds_enabled=True),
        dispose=AsyncMock(side_effect=lambda: order.append("dispose")),
        session_factory=Mock(),
        clock=Mock(),
        store=store,
        **{name: worker(name) for name in (*FEED_WORKERS, *OTHER_WORKERS)},
    )
    return app, order, storage


async def test_lifecycle_loads_before_feeds_and_saves_after_they_stop(lifecycle: Lifecycle) -> None:
    app, order, storage = lifecycle
    async with lifespan(app):
        assert order.index("read") < order.index("scheduler.start")
        assert "write" not in order
    assert order.index("scheduler.stop") < order.index("write") < order.index("dispose")
    assert [event.id for event in storage.saved[0][0]] == [make_event("restored").id]


async def test_partial_startup_still_saves_a_completed_load(lifecycle: Lifecycle) -> None:
    app, order, _ = lifecycle
    app.state.container.evaluator.start.side_effect = RuntimeError("startup failed")
    with pytest.raises(RuntimeError, match="startup failed"):
        async with lifespan(app):
            pytest.fail("Startup must not yield")
    assert order.index("evaluator.stop") < order.index("write") < order.index("dispose")
