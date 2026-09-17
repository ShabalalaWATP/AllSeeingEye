"""Read the live instruments for one scope, but only when the report actually asks.

The reviewed trigger table decides eligibility exactly as it does for the packaged
registers: an ordinary question reads nothing, and an operator's drawn area is itself
the request. Every reading is a count of records the bounded live store still holds
inside the resolved scope, with its window and its limits stated beside it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime

from ase.application.ports.area_geography import AreaGeography, ScopeRequest, ScopeSample
from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.ports.interference import InterferenceCells
from ase.domain.area_assets import InstrumentClass, instrument_triggers
from ase.domain.area_instruments import (
    MAX_INSTRUMENT_EXAMPLES,
    InstrumentReading,
    bound_readings,
)
from ase.domain.aviation import JAM_WINDOW, JamCell
from ase.domain.events import Category, Event, GeoConfidence

INSTRUMENT_POOL = 20_000
THERMAL_TAG = "firms"

_LABELS = {
    InstrumentClass.THERMAL_DETECTIONS: "Satellite thermal detections (NASA FIRMS VIIRS)",
    InstrumentClass.AIRCRAFT_ACTIVITY: "Aircraft currently tracked (ADS-B)",
    InstrumentClass.VESSEL_ACTIVITY: "Vessels currently tracked (AIS)",
    InstrumentClass.GNSS_INTERFERENCE: "Degraded navigation accuracy cells (ADS-B derived)",
}
_BASES = {
    InstrumentClass.THERMAL_DETECTIONS: (
        "A thermal anomaly at a nominal 375 m pixel centre, not a fire boundary and not a "
        "cause. Cloud and overpass timing leave gaps, so an absence is not clearance."
    ),
    InstrumentClass.AIRCRAFT_ACTIVITY: (
        "Aircraft positions as last reported to ADS-B receivers. Coverage is uneven and "
        "excludes anything not transmitting, and a position is not a claim about a mission."
    ),
    InstrumentClass.VESSEL_ACTIVITY: (
        "Vessel positions as last reported by AIS. Transponders can be off or falsified, "
        "coverage is uneven, and a position is not a claim about cargo or intent."
    ),
    InstrumentClass.GNSS_INTERFERENCE: (
        "Cells where tracked aircraft reported low navigation accuracy in the last 24 hours. "
        "This application's own proxy for possible degradation, never confirmation of "
        "jamming or spoofing, and never an attribution of cause."
    ),
}
_CATEGORIES = {
    InstrumentClass.THERMAL_DETECTIONS: Category.DISASTER,
    InstrumentClass.AIRCRAFT_ACTIVITY: Category.AVIATION,
    InstrumentClass.VESSEL_ACTIVITY: Category.MARITIME,
}


def _inside(
    geography: AreaGeography, request: ScopeRequest, samples: tuple[ScopeSample, ...]
) -> frozenset[str]:
    return geography.locate(
        area=request.area,
        country_isos=request.country_isos,
        box=request.box,
        box_label=request.box_label,
        samples=samples,
    )


def eligible_instruments(text: str, *, drawn: bool) -> tuple[InstrumentClass, ...]:
    """A drawn area asks for every instrument; otherwise only the classes named in words."""
    if drawn:
        return tuple(InstrumentClass)
    named = {row.name for row in instrument_triggers(text)}
    return tuple(row for row in InstrumentClass if row.value in named)


def _window_hours(records: Sequence[datetime], now: datetime) -> int:
    """The window the store actually held, never a window the application wishes it had."""
    stamps = [row for row in records if row.utcoffset() is not None and row <= now]
    if not stamps:
        return 1
    return max(1, math.ceil((now - min(stamps)).total_seconds() / 3600))


def _events(store: EventStore, category: Category, tag: str | None) -> list[Event]:
    rows = store.query(EventQuery(categories=frozenset({category}), limit=INSTRUMENT_POOL))
    return [
        row
        for row in rows
        if row.point is not None
        and row.geo_confidence is GeoConfidence.EXACT
        and (tag is None or tag in row.tags)
    ]


def _event_reading(
    geography: AreaGeography,
    instrument: InstrumentClass,
    rows: Sequence[Event],
    now: datetime,
    request: ScopeRequest,
) -> InstrumentReading:
    samples = tuple(
        ScopeSample(row.id, row.point.lon, row.point.lat) for row in rows if row.point is not None
    )
    inside = _inside(geography, request, samples)
    matched = [row for row in rows if row.id in inside]
    examples = tuple(row.title[:200] for row in matched[:MAX_INSTRUMENT_EXAMPLES] if row.title)
    return InstrumentReading(
        instrument.value,
        _LABELS[instrument],
        len(matched),
        len(rows),
        _window_hours([row.published_at for row in rows if row.published_at], now),
        _BASES[instrument],
        examples,
    )


def _cell_reading(
    geography: AreaGeography,
    cells: Sequence[JamCell],
    request: ScopeRequest,
) -> InstrumentReading:
    degraded = [row for row in cells if row.bad and row.level != "green"]
    samples = tuple(ScopeSample(f"{row.lon}:{row.lat}", row.lon, row.lat) for row in degraded)
    inside = _inside(geography, request, samples)
    matched = [row for row in degraded if f"{row.lon}:{row.lat}" in inside]
    examples = tuple(
        f"cell {row.lon:.1f},{row.lat:.1f}: {row.percent_bad:.1f}% of {row.good + row.bad} "
        f"aircraft-hours reported low accuracy"
        for row in matched[:MAX_INSTRUMENT_EXAMPLES]
    )
    return InstrumentReading(
        InstrumentClass.GNSS_INTERFERENCE.value,
        _LABELS[InstrumentClass.GNSS_INTERFERENCE],
        len(matched),
        len(degraded),
        int(JAM_WINDOW.total_seconds() // 3600),
        _BASES[InstrumentClass.GNSS_INTERFERENCE],
        examples,
    )


def sweep_instruments(
    geography: AreaGeography,
    wanted: Sequence[InstrumentClass],
    request: ScopeRequest,
    store: EventStore,
    now: datetime,
    interference: InterferenceCells | None = None,
) -> tuple[InstrumentReading, ...]:
    """One reading per eligible instrument that holds anything at all; nothing is invented."""
    readings: list[InstrumentReading] = []
    for instrument in wanted:
        if instrument is InstrumentClass.GNSS_INTERFERENCE:
            if interference is None:
                continue
            reading = _cell_reading(geography, interference.cells(), request)
        else:
            tag = THERMAL_TAG if instrument is InstrumentClass.THERMAL_DETECTIONS else None
            rows = _events(store, _CATEGORIES[instrument], tag)
            if not rows:
                continue
            reading = _event_reading(geography, instrument, rows, now, request)
        if reading.considered:
            readings.append(reading)
    return bound_readings(tuple(readings))
