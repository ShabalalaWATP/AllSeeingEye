"""Aviation analysis (docs/04 section 5.3): the GNSS interference map and activity counts.

ASE bins reported navigation accuracy into hourly geographic cells. This is a proxy for
possible degradation, not GPSJam's dataset or confirmation of jamming/spoofing. An aircraft
counts once per cell/hour; any low-accuracy report takes precedence in that bucket. The
adjusted low-accuracy share subtracts one observation. NACp 0 to 5 (low or unavailable
accuracy) is the app's explicit assumption, not an attribution of cause.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ase.domain.events import Category, Event

BAD_NACP = 5
CELL_DEGREES = 1.0
JAM_WINDOW = timedelta(hours=24)
AMBER_PERCENT = 2.0
RED_PERCENT = 10.0
MIN_AIRCRAFT = 5
MAX_OBSERVATIONS = 250_000

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
    if (
        not isinstance(nac_p, int | float)
        or isinstance(nac_p, bool)
        or not 0 <= nac_p <= 11
        or not float(nac_p).is_integer()
    ):
        return None
    return nac_p <= BAD_NACP


class JamMap:
    """Bounded aircraft-cell-hour assignments, retaining the oldest overlapping hour."""

    def __init__(
        self,
        size: float = CELL_DEGREES,
        window: timedelta = JAM_WINDOW,
        max_observations: int = MAX_OBSERVATIONS,
    ) -> None:
        self._size = size
        self._window = window
        self._limit = max_observations
        self._assignments = 0
        self._limited_hours: set[datetime] = set()
        self._hours: dict[datetime, dict[CellKey, tuple[set[str], set[str]]]] = {}
        self.updated_at: datetime | None = None

    @property
    def limited(self) -> bool:
        """Some assignments were omitted in the retained window; ratios are partial."""
        return bool(self._limited_hours)

    def observe(self, events: Iterable[Event], now: datetime) -> int:
        """Count each located aircraft with an accuracy field once per cell and hour."""
        self.prune(now)
        counted = 0
        for event in events:
            if event.category is not Category.AVIATION or event.point is None:
                continue
            bad = is_bad(event)
            if bad is None:
                continue
            observed = event.published_at
            if (
                observed is None
                or observed.utcoffset() is None
                or not now - self._window <= observed <= now
            ):
                continue
            hour = observed.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
            bucket = self._hours.setdefault(hour, {})
            key = cell_key(event.point.lon, event.point.lat, self._size)
            identity = str(event.attributes.get("icao_hex") or event.id)
            existing = bucket.get(key)
            known = existing is not None and (identity in existing[0] or identity in existing[1])
            if not known and self._assignments >= self._limit:
                self._limited_hours.add(hour)
                continue
            good_set, bad_set = bucket.setdefault(key, (set(), set()))
            if not known:
                self._assignments += 1
            if bad:
                good_set.discard(identity)
                bad_set.add(identity)
            elif identity not in bad_set:
                good_set.add(identity)
            self.updated_at = max(self.updated_at or observed, observed)
            counted += 1
        return counted

    def prune(self, now: datetime) -> None:
        # Hour precision avoids expiring valid observations early, retaining <25 hours.
        cutoff = (now.astimezone(UTC) - self._window).replace(minute=0, second=0, microsecond=0)
        for hour in [hour for hour in self._hours if hour < cutoff]:
            self._assignments -= sum(
                len(good) + len(bad) for good, bad in self._hours[hour].values()
            )
            del self._hours[hour]
        self._limited_hours.intersection_update(self._hours)

    def cells(self) -> list[JamCell]:
        """Cells with enough aircraft-cell-hour observations, worst first."""
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
