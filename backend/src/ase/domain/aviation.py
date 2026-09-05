"""Aviation analysis (docs/04 section 5.3): the GNSS interference map and activity counts.

The interference map follows the published GPSJam method: aircraft are binned into cells
over a rolling day, an aircraft reporting poor position accuracy counts as "bad", and the
share of bad aircraft (less one, so a lone bad aircraft never colours a cell) sets the
level. Poor accuracy is taken as a navigation accuracy category (`nac_p`) of 5 or below,
which is roughly a 1 km error bound; that threshold is an assumption to revisit.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from ase.domain.events import Category, Event

BAD_NACP = 5
CELL_DEGREES = 1.0
JAM_WINDOW = timedelta(hours=24)
AMBER_PERCENT = 2.0
RED_PERCENT = 10.0
MIN_AIRCRAFT = 5

CellKey = tuple[int, int]


def cell_key(lon: float, lat: float, size: float = CELL_DEGREES) -> CellKey:
    return (int(lon // size), int(lat // size))


@dataclass(frozen=True, slots=True)
class JamCell:
    lon: float
    lat: float
    size: float
    good: int
    bad: int

    @property
    def percent_bad(self) -> float:
        total = self.good + self.bad
        if total == 0:
            return 0.0
        return max(0.0, round(100.0 * (self.bad - 1) / total, 1))

    @property
    def level(self) -> str:
        if self.percent_bad > RED_PERCENT:
            return "red"
        if self.percent_bad >= AMBER_PERCENT:
            return "amber"
        return "green"


def is_bad(event: Event) -> bool | None:
    """True when the aircraft reports poor accuracy, False when good, None when unknown."""
    nac_p = event.attributes.get("nac_p")
    if not isinstance(nac_p, int | float) or isinstance(nac_p, bool):
        return None
    return nac_p <= BAD_NACP


class JamMap:
    """Rolling hourly buckets of good and bad aircraft per cell; a few thousand sets at most."""

    def __init__(self, size: float = CELL_DEGREES, window: timedelta = JAM_WINDOW) -> None:
        self._size = size
        self._window = window
        self._hours: dict[datetime, dict[CellKey, tuple[set[str], set[str]]]] = {}
        self.updated_at: datetime | None = None

    def observe(self, events: Iterable[Event], now: datetime) -> int:
        """Count each located aircraft with an accuracy field once per cell and hour."""
        hour = now.replace(minute=0, second=0, microsecond=0)
        bucket = self._hours.setdefault(hour, {})
        counted = 0
        for event in events:
            if event.category is not Category.AVIATION or event.point is None:
                continue
            bad = is_bad(event)
            if bad is None:
                continue
            key = cell_key(event.point.lon, event.point.lat, self._size)
            good_set, bad_set = bucket.setdefault(key, (set(), set()))
            identity = str(event.attributes.get("icao_hex") or event.id)
            (bad_set if bad else good_set).add(identity)
            counted += 1
        self.updated_at = now
        self.prune(now)
        return counted

    def prune(self, now: datetime) -> None:
        cutoff = now - self._window
        for hour in [hour for hour in self._hours if hour < cutoff]:
            del self._hours[hour]

    def cells(self) -> list[JamCell]:
        """Cells with enough aircraft over the window, worst first."""
        good: Counter[CellKey] = Counter()
        bad: Counter[CellKey] = Counter()
        for bucket in self._hours.values():
            for key, (good_set, bad_set) in bucket.items():
                good[key] += len(good_set)
                bad[key] += len(bad_set)
        cells = [
            JamCell(
                lon=(key[0] + 0.5) * self._size,
                lat=(key[1] + 0.5) * self._size,
                size=self._size,
                good=good[key],
                bad=bad[key],
            )
            for key in set(good) | set(bad)
            if good[key] + bad[key] >= MIN_AIRCRAFT
        ]
        cells.sort(key=lambda cell: (-cell.percent_bad, -cell.bad, cell.lon, cell.lat))
        return cells


def military_by_country(events: Iterable[Event]) -> Counter[str]:
    """Military aircraft currently over each nation, by ISO code."""
    counts: Counter[str] = Counter()
    for event in events:
        if event.category is Category.AVIATION and "military" in event.tags and event.country_iso:
            counts[event.country_iso] += 1
    return counts


def tagged(events: Iterable[Event], tag: str) -> list[Event]:
    return [event for event in events if tag in event.tags]
