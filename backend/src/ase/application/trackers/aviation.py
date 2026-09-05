"""The aviation tracker: a sampler that keeps baselines and the interference map current,
and a board computed on request from the live store."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog

from ase.application.ports import Clock
from ase.application.ports.baselines import BaselineRepository, BaselineSink
from ase.application.ports.feeds import EventQuery, EventStore
from ase.domain.aviation import JamCell, JamMap, military_by_country, tagged
from ase.domain.events import Category, Event

log = structlog.get_logger(__name__)

SAMPLE_INTERVAL = timedelta(minutes=5)
BASELINE_DAYS = 30
POOL = 20_000
KIND_MILITARY = "military_aircraft"
KIND_AREA = "area_aircraft"
KIND_EMERGENCY = "emergency_squawks"
SleepFn = Callable[[float], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class WatchedArea:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class CountryActivity:
    iso: str
    count: int
    baseline: float | None

    @property
    def ratio(self) -> float | None:
        if self.baseline is None or self.baseline == 0:
            return None
        return round(self.count / self.baseline, 2)


@dataclass(frozen=True, slots=True)
class AreaActivity:
    id: str
    name: str
    count: int
    military: int
    baseline: float | None


@dataclass(frozen=True, slots=True)
class AviationBoard:
    military_total: int
    interesting: int
    ladd: int
    pia: int
    by_country: tuple[CountryActivity, ...]
    emergencies: tuple[Event, ...]
    areas: tuple[AreaActivity, ...]
    jam_amber: int
    jam_red: int
    jam_updated_at: datetime | None


def aviation_events(store: EventStore) -> list[Event]:
    return store.query(EventQuery(categories=frozenset({Category.AVIATION}), limit=POOL))


def samples_for(
    events: Sequence[Event], areas: Sequence[WatchedArea]
) -> list[tuple[str, str, int]]:
    """What one sample writes: military per nation, aircraft per area, emergencies."""
    rows = [(KIND_MILITARY, iso, count) for iso, count in military_by_country(events).items()]
    rows.extend((KIND_AREA, area.id, len(tagged(events, f"area_{area.id}"))) for area in areas)
    rows.append((KIND_EMERGENCY, "all", len(tagged(events, "emergency"))))
    return rows


class AviationMonitor:
    """Every few minutes: feed the interference map and write the hour's baselines."""

    def __init__(
        self,
        store: EventStore,
        jam: JamMap,
        sink: BaselineSink,
        clock: Clock,
        areas: Sequence[WatchedArea] = (),
        *,
        interval: timedelta = SAMPLE_INTERVAL,
        sleep: SleepFn = asyncio.sleep,
    ) -> None:
        self._store = store
        self._jam = jam
        self._sink = sink
        self._clock = clock
        self._areas = tuple(areas)
        self._interval = interval
        self._sleep = sleep
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()

    async def sample(self) -> int:
        now = self._clock.now()
        events = aviation_events(self._store)
        counted = self._jam.observe(events, now)
        hour = now.replace(minute=0, second=0, microsecond=0)
        await self._sink.record_many(hour, samples_for(events, self._areas))
        return counted

    async def start(self) -> None:
        if self._task is None:
            self._stopping.clear()
            self._task = asyncio.create_task(self._run(), name="aviation-monitor")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                await self.sample()
            except Exception:
                log.warning("aviation.sample_failed", exc_info=True)
            await self._sleep(self._interval.total_seconds())


class AviationService:
    """The board and the interference cells, computed from the store when asked."""

    def __init__(
        self, store: EventStore, jam: JamMap, clock: Clock, areas: Sequence[WatchedArea] = ()
    ) -> None:
        self._store = store
        self._jam = jam
        self._clock = clock
        self._areas = tuple(areas)

    @property
    def baseline_since(self) -> datetime:
        return self._clock.now() - timedelta(days=BASELINE_DAYS)

    def board(
        self, military_means: Mapping[str, float], area_means: Mapping[str, float]
    ) -> AviationBoard:
        events = aviation_events(self._store)
        counts = military_by_country(events)
        by_country = tuple(
            sorted(
                (
                    CountryActivity(iso, count, military_means.get(iso))
                    for iso, count in counts.items()
                ),
                key=lambda row: (-row.count, row.iso),
            )[:25]
        )
        areas = tuple(
            AreaActivity(
                id=area.id,
                name=area.name,
                count=len(tagged(events, f"area_{area.id}")),
                military=len(
                    [e for e in tagged(events, f"area_{area.id}") if "military" in e.tags]
                ),
                baseline=area_means.get(area.id),
            )
            for area in self._areas
        )
        cells = self._jam.cells()
        emergencies = sorted(
            tagged(events, "emergency"), key=lambda e: (-(e.severity or 0), e.title)
        )
        return AviationBoard(
            military_total=len(tagged(events, "military")),
            interesting=len(tagged(events, "interesting")),
            ladd=len(tagged(events, "ladd")),
            pia=len(tagged(events, "pia")),
            by_country=by_country,
            emergencies=tuple(emergencies[:50]),
            areas=areas,
            jam_amber=sum(1 for cell in cells if cell.level == "amber"),
            jam_red=sum(1 for cell in cells if cell.level == "red"),
            jam_updated_at=self._jam.updated_at,
        )

    def jam_cells(self) -> list[JamCell]:
        return self._jam.cells()


async def board_with_baselines(
    service: AviationService, baselines: BaselineRepository
) -> AviationBoard:
    """The board with the last month's means from the samples table."""
    since = service.baseline_since
    return service.board(
        await baselines.means(KIND_MILITARY, since), await baselines.means(KIND_AREA, since)
    )


async def background(service: AviationService, baselines: BaselineRepository) -> str:
    return summary_text(await board_with_baselines(service, baselines))


def summary_text(board: AviationBoard) -> str:
    """The board in a paragraph, for the aviation report's background."""
    top = ", ".join(
        f"{row.iso} {row.count}" + (f" (baseline {row.baseline:.1f})" if row.baseline else "")
        for row in board.by_country[:8]
    )
    areas = ", ".join(
        f"{area.name} {area.count} ({area.military} military)" for area in board.areas
    )
    return (
        f"Military aircraft tracked now: {board.military_total}; interesting {board.interesting}, "
        f"LADD {board.ladd}, PIA {board.pia}. By nation: {top or 'none'}. Watched areas: "
        f"{areas or 'none'}. Emergency squawks now: {len(board.emergencies)}. GNSS interference "
        f"cells over the last day: {board.jam_red} red, {board.jam_amber} amber."
    )
