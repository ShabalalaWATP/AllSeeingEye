"""KAN-200: publication recovers from failures, host pacing does not spend fetch
budgets, and disabled or retired sources do not return from the live store."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import timedelta

import pytest
from httpx import AsyncClient

from ase.adapters.feeds.host_pacing import HostPacer
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.fetch_budget import UpstreamQueue, pausable_timeout
from ase.application.feeds.health import HealthRegistry
from ase.application.feeds.live_snapshot import LiveStoreSnapshots
from ase.application.feeds.pipeline import Normaliser, Pipeline
from ase.application.feeds.scheduler import FeedScheduler
from ase.application.ports.feeds import BusMessage
from ase.application.ports.live_snapshot import SnapshotLoad
from ase.container import Container
from ase.domain.events import Category, Event
from ase.domain.users import User
from event_app_fixtures import email_sender, feed_connectors  # noqa: F401
from feeds_helpers import NOW, FakeClock, FakeConnector, make_event, make_spec
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_feed_scheduler_reliability import Admission

TELEGRAM = "https://t.me/s/channel"


class RecordingBus:
    def __init__(self) -> None:
        self.messages: list[BusMessage] = []

    async def publish(self, message: BusMessage) -> None:
        self.messages.append(message)

    def kinds(self) -> list[str]:
        return [message.kind for message in self.messages]

    def subscribe(self) -> None:  # pragma: no cover - not used by the poller
        raise NotImplementedError


class FailingGrader:
    def regrade(self, events: Sequence[Event]) -> list[Event]:
        raise RuntimeError("grading broke")


class HangingGrader:
    def regrade(self, events: Sequence[Event]) -> list[Event]:  # pragma: no cover
        return []

    async def regrade_cooperatively(self, events: Sequence[Event]) -> list[Event]:
        await asyncio.Event().wait()
        return []


def scheduler(connectors, bus=None, store=None, **options) -> FeedScheduler:  # type: ignore[no-untyped-def]
    return FeedScheduler(
        connectors,
        Pipeline([Normaliser()]),
        store or InMemoryEventStore(),
        bus or RecordingBus(),
        options.pop("health", None) or HealthRegistry(),
        FakeClock(NOW),
        **options,
    )


def feed(source_id: str = "feed") -> FakeConnector:
    return FakeConnector(make_spec(source_id), [make_event(source_id, source_id=source_id)])


async def test_a_grading_fault_still_publishes_the_stored_batch_and_counts_one_poll() -> None:
    bus, store, health = RecordingBus(), InMemoryEventStore(), HealthRegistry()
    poller = scheduler([feed()], bus, store, grader=FailingGrader(), health=health)
    connector = poller.connectors[0]
    assert (await poller.poll_once(connector)).ok
    assert bus.kinds() == ["event.upsert", "source.health"]
    published: list[Event] = bus.messages[0].payload["events"]  # type: ignore[assignment]
    assert [e.id for e in published] == [make_event("feed", source_id="feed").id]
    assert (await poller.poll_once(connector)).ok
    assert health.get("feed").polls == 2


async def test_a_deadline_after_the_store_write_requests_a_resync() -> None:
    bus, store, health = RecordingBus(), InMemoryEventStore(), HealthRegistry()
    poller = scheduler(
        [feed()],
        bus,
        store,
        grader=HangingGrader(),
        health=health,
        processing_timeout=timedelta(seconds=0.05),
    )
    outcome = await poller.poll_once(poller.connectors[0])
    assert not outcome.ok and "deadline" in (outcome.error or "")
    assert store.get(make_event("feed", source_id="feed").id) is not None
    assert bus.kinds() == ["event.resync", "source.health"]
    assert bus.messages[0].payload == {
        "reason": "snapshot_required",
        "source_id": "feed",
        "categories": (Category.DISASTER,),
    }
    assert health.get("feed").polls == 1


class PacerClock:
    """A fake monotonic clock; each pacing sleep advances it after a gate opens."""

    def __init__(self, real_seconds: float = 0.0) -> None:
        self.now = 0.0
        self.real_seconds = real_seconds
        self.sleeping = asyncio.Event()
        self.release = asyncio.Event()
        self.release.set()

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.sleeping.set()
        await self.release.wait()
        # Real waiting longer than the fetch deadline proves the deadline was paused.
        await asyncio.sleep(self.real_seconds)
        self.now += seconds


class PacedConnector(FakeConnector):
    def __init__(self, source_id: str, pacer: HostPacer, clock: PacerClock) -> None:
        super().__init__(make_spec(source_id), [make_event(source_id, source_id=source_id)])
        self.pacer, self.clock = pacer, clock
        self.started_at: float | None = None

    async def fetch(self) -> list[Event]:
        await self.pacer.wait(TELEGRAM)
        self.started_at = self.clock.monotonic()
        return await super().fetch()


async def test_start_up_burst_queues_for_the_host_without_timing_out() -> None:
    clock = PacerClock(real_seconds=0.02)
    pacer = HostPacer({"t.me": 5.0}, monotonic=clock.monotonic, sleep=clock.sleep)
    channels = [PacedConnector(f"telegram_{n}", pacer, clock) for n in range(6)]
    poller = scheduler(channels, fetch_timeout=timedelta(seconds=0.05), fetch_concurrency=2)
    outcomes = await asyncio.gather(*(poller.poll_once(c) for c in channels))
    # Five queued turns take 0.1 s of real time, twice the fetch deadline.
    assert all(outcome.ok for outcome in outcomes), [o.error for o in outcomes]
    assert sorted(c.started_at or 0.0 for c in channels) == [0.0, 5.0, 10.0, 15.0, 20.0, 25.0]


async def test_queued_requests_return_their_fetch_slot() -> None:
    clock = PacerClock()
    pacer = HostPacer({"t.me": 5.0}, monotonic=clock.monotonic, sleep=clock.sleep)
    await pacer.wait(TELEGRAM)  # The next t.me turn is five fake seconds away.
    clock.release.clear()
    paced, plain = PacedConnector("telegram_a", pacer, clock), feed("plain")
    poller = scheduler([paced, plain], fetch_concurrency=1)
    queued = asyncio.create_task(poller.poll_once(paced))
    await asyncio.wait_for(clock.sleeping.wait(), 2)
    # With the only slot handed back, an unrelated feed fetches while t.me waits.
    assert (await asyncio.wait_for(poller.poll_once(plain), 2)).ok
    clock.release.set()
    assert (await asyncio.wait_for(queued, 2)).ok
    assert paced.started_at == 5.0


async def test_pausable_timeout_stops_only_while_queued() -> None:
    async with pausable_timeout(0.05), UpstreamQueue():
        await asyncio.sleep(0.15)
    with pytest.raises(TimeoutError):
        async with pausable_timeout(0.05):
            await asyncio.sleep(0.15)


class Storage:
    def __init__(self, events: Sequence[Event]) -> None:
        self.events = tuple(events)

    def read(self) -> SnapshotLoad:
        return SnapshotLoad(self.events)

    def write(self, events: Sequence[Event], saved_at: object) -> bool:  # pragma: no cover
        return True


async def _idle(_seconds: float) -> None:  # pragma: no cover - the loop never runs here
    await asyncio.Event().wait()


def _snapshot_events() -> list[Event]:
    return [make_event(source, source_id=source) for source in ("live", "off", "retired")]


async def test_restore_keeps_only_registered_enabled_sources() -> None:
    admission = Admission()
    admission.disabled.add("off")
    store = InMemoryEventStore()
    snapshots = LiveStoreSnapshots(
        store,
        Storage(_snapshot_events()),
        FakeClock(NOW),
        interval=timedelta(minutes=5),
        sleep=_idle,
        registered={"live", "off"},
        admission=admission,  # type: ignore[arg-type]
    )
    assert await snapshots.load() == 1
    assert [event.source_id for event in store.retained()] == ["live"]


async def test_restore_fails_closed_when_admission_is_unavailable() -> None:
    class Broken(Admission):
        async def enabled_many(self, source_ids: tuple[str, ...]) -> dict[str, bool]:
            raise RuntimeError("database down")

    store = InMemoryEventStore()
    snapshots = LiveStoreSnapshots(
        store,
        Storage(_snapshot_events()),
        FakeClock(NOW),
        interval=timedelta(minutes=5),
        sleep=_idle,
        registered={"live"},
        admission=Broken(),  # type: ignore[arg-type]
    )
    assert await snapshots.load() == 0


async def test_withdrawing_a_source_removes_its_children_and_announces_expiry() -> None:
    bus, store = RecordingBus(), InMemoryEventStore()
    parent, child, other = feed("usgs_earthquakes"), feed("research-usgs-area"), feed("other")
    poller = scheduler([parent, child, other], bus, store)
    store.upsert([*parent.events, *child.events, *other.events])
    assert await poller.withdraw("usgs_earthquakes") == 2
    assert [event.source_id for event in store.retained()] == ["other"]
    assert bus.kinds() == ["event.expire"]
    assert set(bus.messages[0].payload["ids"]) == {  # type: ignore[arg-type]
        parent.events[0].id,
        child.events[0].id,
    }
    assert await poller.withdraw("unknown") == 0


async def test_disabling_a_source_at_runtime_purges_its_live_events(
    client: AsyncClient, container: Container, admin: User
) -> None:
    event = make_event("live", source_id="fake_feed")
    container.store.upsert([event])
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = await client.patch(
        "/api/admin/sources/fake_feed/activation", headers=bearer(token), json={"enabled": False}
    )
    assert response.status_code == 204
    assert container.store.get(event.id) is None
