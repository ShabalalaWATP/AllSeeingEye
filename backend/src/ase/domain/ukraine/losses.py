"""Claimed loss figures: a belligerent's own daily statement, kept as a claim."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType

JsonScalar = str | int | float | bool | None

MAX_CLAIMS = 100
MAX_COUNT = 1_000_000_000
INVASION_DAY = date(2022, 2, 24)

# Category keys as the General Staff summary publishes them, with plain labels.
LOSS_CATEGORIES: Mapping[str, str] = MappingProxyType(
    {
        "personnel_units": "Personnel",
        "tanks": "Tanks",
        "armoured_fighting_vehicles": "Armoured fighting vehicles",
        "artillery_systems": "Artillery systems",
        "mlrs": "Multiple rocket launchers",
        "aa_warfare_systems": "Air defence systems",
        "planes": "Aircraft",
        "helicopters": "Helicopters",
        "uav_systems": "Drones",
        "cruise_missiles": "Cruise missiles",
        "warships_cutters": "Warships and boats",
        "submarines": "Submarines",
        "vehicles_fuel_tanks": "Vehicles and fuel tankers",
        "special_military_equip": "Special equipment",
        "atgm_srbm_systems": "Missile launchers",
    }
)
HEADLINE_CATEGORIES: tuple[str, ...] = (
    "personnel_units",
    "tanks",
    "armoured_fighting_vehicles",
    "artillery_systems",
    "uav_systems",
    "cruise_missiles",
)


@dataclass(frozen=True, slots=True)
class ClaimedLosses:
    """One day's cumulative claim with the day's stated increase, never a verified count."""

    reported_on: date
    day: int
    source_url: str | None
    totals: Mapping[str, int]
    increase: Mapping[str, int]


def war_day(on: date) -> int:
    """Day count from the full-scale invasion, the convention the General Staff uses."""
    return (on - INVASION_DAY).days + 1


def _count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = int(value)
    return number if number == value and 0 <= number <= MAX_COUNT else None


def parse_counts(raw: object) -> dict[str, int]:
    """Known categories with non-negative integer values; unknown keys are dropped."""
    if not isinstance(raw, dict):
        return {}
    counts: dict[str, int] = {}
    for key in LOSS_CATEGORIES:
        number = _count(raw.get(key))
        if number is not None:
            counts[key] = number
    return counts


def claim_attributes(claim: ClaimedLosses) -> dict[str, JsonScalar]:
    """Flatten a claim into event attributes (bounded: 15 categories twice plus the day)."""
    attributes: dict[str, JsonScalar] = {"day": claim.day}
    for key, value in claim.totals.items():
        attributes[f"total_{key}"] = value
    for key, value in claim.increase.items():
        attributes[f"increase_{key}"] = value
    return attributes


def claim_from_attributes(
    reported_on: date, source_url: str | None, attributes: Mapping[str, JsonScalar]
) -> ClaimedLosses | None:
    """Rebuild a claim from stored attributes; missing or malformed figures give None."""
    day = _count(attributes.get("day"))
    totals = parse_counts({key: attributes.get(f"total_{key}") for key in LOSS_CATEGORIES})
    if day is None or not totals:
        return None
    increase = parse_counts({key: attributes.get(f"increase_{key}") for key in LOSS_CATEGORIES})
    return ClaimedLosses(
        reported_on=reported_on,
        day=day,
        source_url=source_url,
        totals=MappingProxyType(totals),
        increase=MappingProxyType(increase),
    )
