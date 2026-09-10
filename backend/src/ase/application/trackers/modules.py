"""Maritime, space and cyber boards, computed from the live store when asked."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from ase.application.ports import Clock
from ase.application.ports.feeds import EventQuery, EventStore
from ase.domain.events import Category, Event
from ase.domain.evidence_time import publication_order

POOL = 5_000
FORTNIGHT = timedelta(days=14)
WEEK = timedelta(days=7)
DAY = timedelta(days=1)
LIST_LIMIT = 50


@dataclass(frozen=True, slots=True)
class Tally:
    key: str
    count: int
    max_severity: float | None


@dataclass(frozen=True, slots=True)
class MaritimeBoard:
    warnings_total: int
    located: int
    by_area: tuple[Tally, ...]
    by_kind: tuple[Tally, ...]
    notable: tuple[Event, ...]
    latest: tuple[Event, ...]


@dataclass(frozen=True, slots=True)
class SpaceBoard:
    stations: tuple[Event, ...]
    launches: tuple[Event, ...]
    kp: float | None
    kp_level: str | None
    alerts_24h: int
    latest_alerts: tuple[Event, ...]


@dataclass(frozen=True, slots=True)
class CyberBoard:
    outages_24h: int
    outages_by_country: tuple[Tally, ...]
    ransomware_7d: int
    ransomware_by_country: tuple[Tally, ...]
    ransomware_by_group: tuple[Tally, ...]
    kev_7d: int
    latest_outages: tuple[Event, ...]
    latest_claims: tuple[Event, ...]
    latest_kev: tuple[Event, ...]


def tally(events: list[Event], key_of: Any, limit: int = 12) -> tuple[Tally, ...]:
    """Counts and the worst severity per key, largest first."""
    counts: Counter[str] = Counter()
    worst: dict[str, float] = {}
    for event in events:
        key = key_of(event)
        if not key:
            continue
        counts[key] += 1
        if event.severity is not None:
            worst[key] = max(worst.get(key, 0.0), event.severity)
    rows = [Tally(key, count, worst.get(key)) for key, count in counts.items()]
    rows.sort(key=lambda row: (-row.count, row.key))
    return tuple(rows[:limit])


def newest(events: list[Event], limit: int = LIST_LIMIT) -> tuple[Event, ...]:
    return tuple(sorted(events, key=publication_order, reverse=True)[:limit])


class ModuleService:
    def __init__(self, store: EventStore, clock: Clock) -> None:
        self._store = store
        self._clock = clock

    def _events(self, category: Category, since: timedelta) -> list[Event]:
        now = self._clock.now()
        return self._store.query(
            EventQuery(categories=frozenset({category}), since=now - since, limit=POOL)
        )

    def maritime_board(self) -> MaritimeBoard:
        warnings = [
            e for e in self._events(Category.MARITIME, FORTNIGHT) if e.subtype == "navarea_warning"
        ]
        notable = [e for e in warnings if (e.severity or 0) >= 0.6]
        return MaritimeBoard(
            warnings_total=len(warnings),
            located=sum(1 for e in warnings if e.point is not None),
            by_area=tally(warnings, lambda e: str(e.attributes.get("nav_area") or "")),
            by_kind=tally(warnings, lambda e: str(e.attributes.get("kind") or "")),
            notable=newest(notable, 20),
            latest=newest(warnings),
        )

    def space_board(self) -> SpaceBoard:
        now = self._clock.now()
        events = self._events(Category.SPACE, WEEK)
        stations = [e for e in events if e.subtype == "satellite"]
        launches = [e for e in events if e.subtype == "launch" and _upcoming(e, now)]
        launches.sort(key=lambda e: _net(e) or now)
        kp_events = [e for e in events if e.subtype == "geomagnetic"]
        kp_event = max(kp_events, key=publication_order, default=None)
        alerts = [
            e
            for e in events
            if e.source_id in ("noaa_swpc_alerts", "swpc_alerts")
            and e.subtype in ("space_weather_alert", "space_weather")
        ]
        recent = [e for e in alerts if e.published_at is not None and e.published_at >= now - DAY]
        kp_value = kp_event.attributes.get("kp") if kp_event is not None else None
        return SpaceBoard(
            stations=tuple(sorted(stations, key=lambda e: e.title)),
            launches=tuple(launches[:20]),
            kp=float(kp_value) if isinstance(kp_value, int | float) else None,
            kp_level=next(
                (t for t in ("storm", "active", "quiet") if kp_event and t in kp_event.tags), None
            ),
            alerts_24h=len(recent),
            latest_alerts=newest(alerts, 20),
        )

    def cyber_board(self) -> CyberBoard:
        now = self._clock.now()
        events = self._events(Category.CYBER, WEEK)
        outages = [
            e
            for e in events
            if e.subtype == "outage" and e.published_at is not None and e.published_at >= now - DAY
        ]
        claims = [e for e in events if e.subtype == "ransomware"]
        kev = [e for e in events if e.source_id == "cisa_kev"]
        return CyberBoard(
            outages_24h=len(outages),
            outages_by_country=tally(outages, lambda e: e.country_iso or ""),
            ransomware_7d=len(claims),
            ransomware_by_country=tally(claims, lambda e: e.country_iso or ""),
            ransomware_by_group=tally(claims, lambda e: str(e.attributes.get("group") or "")),
            kev_7d=len(kev),
            latest_outages=newest(outages, 30),
            latest_claims=newest(claims, 30),
            latest_kev=newest(kev, 30),
        )


def _net(event: Event) -> datetime | None:
    value = event.attributes.get("net")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _upcoming(event: Event, now: datetime) -> bool:
    net = _net(event)
    return net is not None and net >= now - DAY


def maritime_summary(board: MaritimeBoard) -> str:
    areas = ", ".join(f"NAVAREA {row.key} {row.count}" for row in board.by_area[:8])
    kinds = ", ".join(f"{row.key} {row.count}" for row in board.by_kind)
    return (
        f"Active broadcast warnings in the last fortnight: {board.warnings_total} "
        f"({board.located} with positions). By area: {areas or 'none'}. By kind: {kinds or 'none'}."
    )


def cyber_summary(board: CyberBoard) -> str:
    outages = ", ".join(f"{row.key} {row.count}" for row in board.outages_by_country[:8])
    groups = ", ".join(f"{row.key} {row.count}" for row in board.ransomware_by_group[:8])
    countries = ", ".join(f"{row.key} {row.count}" for row in board.ransomware_by_country[:8])
    return (
        f"Internet outage alerts in the last day: {board.outages_24h} "
        f"(by nation: {outages or 'none'}). "
        f"Ransomware claims in the last week: {board.ransomware_7d} (by group: {groups or 'none'}; "
        f"by nation: {countries or 'none'}). Known exploited vulnerabilities added in the week: "
        f"{board.kev_7d}."
    )
