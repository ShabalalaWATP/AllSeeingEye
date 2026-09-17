"""Honest geography for one report: what is genuinely inside the scope, and what is not.

Three separate things are kept separate here. Where the scope came from and what that
basis cannot tell you. How much of the selected evidence is actually located inside it,
as opposed to attached to it by a country code or a publisher's remit. And whether any
recorded baseline exists to say if activity is normal, which is usually no.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ase.domain.area_instruments import (
    NO_INSTRUMENTS,
    InstrumentReading,
    bound_readings,
    readings_from_list,
    readings_to_list,
)
from ase.domain.area_inventory import MAX_LISTED_ITEMS, RegisterEntry, RegisterItem

CONTEXT_POLICY_VERSION = "ase-area-context-v1"
MAX_BREAKDOWN_ROWS = 12
MAX_BASELINES = 8

NO_BASELINE = (
    "No recorded baseline covers this scope. The application stores hourly activity samples "
    "only for tracked military aircraft by country, for its fixed watched air areas and for "
    "emergency squawks; it holds no baseline for an arbitrary outline or for any other feed. "
    "Nothing here says whether the period was busier or quieter than usual."
)
CONTAINMENT_NOTE = (
    "Being selected for this report is a collection choice, not a location. A country code "
    "or a publisher's remit is never a location claim, and an item placed at a country "
    "centroid is never presented as inside the scope."
)


@dataclass(frozen=True, slots=True)
class ScopeReceipt:
    """Where the geography came from, and what that basis cannot establish."""

    basis: str
    label: str
    limitation: str

    def __post_init__(self) -> None:
        if not self.basis or not self.label or not self.limitation:
            raise ValueError("A scope receipt needs a basis, a label and its limitation")

    def describe(self) -> str:
        return f"Scope: {self.label} [{self.basis}]. {self.limitation}"


@dataclass(frozen=True, slots=True)
class ContainmentSplit:
    """Selected evidence by how well its location is actually known, never by assumption."""

    inside_exact: int = 0
    outside_exact: int = 0
    place_level: int = 0
    country_level: int = 0
    unlocated: int = 0

    def __post_init__(self) -> None:
        if any(
            value < 0
            for value in (
                self.inside_exact,
                self.outside_exact,
                self.place_level,
                self.country_level,
                self.unlocated,
            )
        ):
            raise ValueError("Containment counts cannot be negative")

    @property
    def total(self) -> int:
        return (
            self.inside_exact
            + self.outside_exact
            + self.place_level
            + self.country_level
            + self.unlocated
        )

    def describe(self) -> str:
        return (
            f"Containment of the {self.total} selected item(s): {self.inside_exact} precisely "
            f"located inside the scope; {self.outside_exact} precisely located outside it; "
            f"{self.place_level} placed only at a city or region level, so their position is a "
            f"place centre and not an exact location; {self.country_level} placed only at "
            f"country level, which is commonly a country centroid; {self.unlocated} with no "
            f"location at all. {CONTAINMENT_NOTE}"
        )


@dataclass(frozen=True, slots=True)
class BreakdownRow:
    name: str
    count: int

    def __post_init__(self) -> None:
        if not self.name or len(self.name) > 120 or self.count < 0:
            raise ValueError("Breakdown rows need a bounded name and a non-negative count")


@dataclass(frozen=True, slots=True)
class AreaBreakdown:
    """Where inside the scope the precisely located items fall, from packaged geometry only."""

    dataset: str
    attribution: str
    rows: tuple[BreakdownRow, ...]
    unassigned: int = 0

    def __post_init__(self) -> None:
        if not self.dataset or not self.attribution or len(self.rows) > MAX_BREAKDOWN_ROWS:
            raise ValueError("A breakdown needs an attributed dataset and bounded rows")
        if self.unassigned < 0:
            raise ValueError("Unassigned counts cannot be negative")

    def describe(self) -> str:
        rows = ", ".join(f"{row.name} {row.count}" for row in self.rows) or "none"
        extra = (
            f" {self.unassigned} precisely located item(s) fell in no listed unit."
            if self.unassigned
            else ""
        )
        return (
            f"Within the scope, by {self.dataset}: {rows}.{extra} "
            f"{self.attribution} Only precisely located items are placed; "
            "boundary geometry is approximate and a unit is not an area of control."
        )


@dataclass(frozen=True, slots=True)
class BaselineComparison:
    """One recorded aggregate against its own recent mean, with the unit stated exactly."""

    kind: str
    key: str
    label: str
    observed: int
    mean: float | None
    days: int
    basis: str

    def __post_init__(self) -> None:
        if not self.kind or not self.key or not self.label or not self.basis:
            raise ValueError("A baseline comparison needs its kind, key, label and basis")
        if self.observed < 0 or self.days <= 0 or (self.mean is not None and self.mean < 0):
            raise ValueError("Baseline values must be non-negative over a positive window")

    def describe(self) -> str:
        if self.mean is None:
            return f"{self.label}: {self.observed} now; no recorded mean for this key. {self.basis}"
        ratio = "" if self.mean == 0 else f" ({self.observed / self.mean:.1f}x the mean)"
        return (
            f"{self.label}: {self.observed} now against a {self.days}-day mean of "
            f"{self.mean:.1f}{ratio}. {self.basis}"
        )


@dataclass(frozen=True, slots=True)
class AreaGeographyResult:
    """What the packaged geometry alone can say about one scope."""

    scope: ScopeReceipt
    containment: ContainmentSplit
    breakdown: tuple[AreaBreakdown, ...] = ()
    registers: tuple[RegisterEntry, ...] = ()


@dataclass(frozen=True, slots=True)
class AreaContext:
    """The geography receipt carried with a report version, beside its collection receipt."""

    scope: ScopeReceipt
    containment: ContainmentSplit
    breakdown: tuple[AreaBreakdown, ...] = ()
    baselines: tuple[BaselineComparison, ...] = ()
    baseline_note: str = NO_BASELINE
    coverage: tuple[RegisterEntry, ...] = ()
    instruments: tuple[InstrumentReading, ...] = ()
    instrument_note: str = NO_INSTRUMENTS
    policy_version: str = CONTEXT_POLICY_VERSION

    def __post_init__(self) -> None:
        if len(self.baselines) > MAX_BASELINES or len(self.breakdown) > 4:
            raise ValueError("Area context exceeds its reviewed bounds")
        bound_readings(self.instruments)
        if self.policy_version != CONTEXT_POLICY_VERSION:
            raise ValueError("Unsupported area context policy")

    def describe(self) -> str:
        parts = [self.scope.describe(), self.containment.describe()]
        parts.extend(row.describe() for row in self.breakdown)
        parts.extend(
            f"Cached coverage: {row.dataset_name}. {row.describe()}" for row in self.coverage
        )
        parts.extend(f"Instrument: {row.describe()}" for row in self.instruments)
        if not self.instruments:
            parts.append(self.instrument_note)
        parts.append(
            "Is this normal? " + " ".join(row.describe() for row in self.baselines)
            if self.baselines
            else "Is this normal? " + self.baseline_note
        )
        if self.baselines:
            parts.append(self.baseline_note)
        return "Area context (" + self.policy_version + "). " + " ".join(parts)


def _rows(value: Any, limit: int) -> list[Mapping[str, Any]]:
    if not isinstance(value, list | tuple) or len(value) > limit:
        raise ValueError("Invalid frozen area context rows")
    if any(not isinstance(row, Mapping) for row in value):
        raise ValueError("Frozen area context rows must be objects")
    rows: list[Mapping[str, Any]] = list(value)
    return rows


def context_to_dict(value: AreaContext | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "policy_version": value.policy_version,
        "scope": {
            "basis": value.scope.basis,
            "label": value.scope.label,
            "limitation": value.scope.limitation,
        },
        "containment": {
            "inside_exact": value.containment.inside_exact,
            "outside_exact": value.containment.outside_exact,
            "place_level": value.containment.place_level,
            "country_level": value.containment.country_level,
            "unlocated": value.containment.unlocated,
        },
        "breakdown": [
            {
                "dataset": row.dataset,
                "attribution": row.attribution,
                "unassigned": row.unassigned,
                "rows": [{"name": item.name, "count": item.count} for item in row.rows],
            }
            for row in value.breakdown
        ],
        "baselines": [
            {
                "kind": row.kind,
                "key": row.key,
                "label": row.label,
                "observed": row.observed,
                "mean": row.mean,
                "days": row.days,
                "basis": row.basis,
            }
            for row in value.baselines
        ],
        "baseline_note": value.baseline_note,
        "coverage": [
            {
                "asset_class": row.asset_class,
                "dataset_id": row.dataset_id,
                "dataset_name": row.dataset_name,
                "count": row.count,
                "as_of": row.as_of,
                "attribution": row.attribution,
                "matched_by": row.matched_by,
                "listed": [
                    {
                        "name": item.name,
                        "country": item.country,
                        "precision": item.precision,
                        "url": item.url,
                    }
                    for item in row.listed
                ],
            }
            for row in value.coverage
        ],
        "instruments": readings_to_list(value.instruments),
        "instrument_note": value.instrument_note,
    }


def context_from_dict(data: Mapping[str, Any] | None) -> AreaContext | None:
    if data is None:
        return None
    if data.get("policy_version") != CONTEXT_POLICY_VERSION:
        raise ValueError("Unsupported frozen area context policy")
    scope, containment = data["scope"], data["containment"]
    return AreaContext(
        ScopeReceipt(scope["basis"], scope["label"], scope["limitation"]),
        ContainmentSplit(
            int(containment["inside_exact"]),
            int(containment["outside_exact"]),
            int(containment["place_level"]),
            int(containment["country_level"]),
            int(containment["unlocated"]),
        ),
        tuple(
            AreaBreakdown(
                row["dataset"],
                row["attribution"],
                tuple(BreakdownRow(item["name"], int(item["count"])) for item in row["rows"]),
                int(row.get("unassigned", 0)),
            )
            for row in _rows(data.get("breakdown", ()), 4)
        ),
        tuple(
            BaselineComparison(
                row["kind"],
                row["key"],
                row["label"],
                int(row["observed"]),
                None if row.get("mean") is None else float(row["mean"]),
                int(row["days"]),
                row["basis"],
            )
            for row in _rows(data.get("baselines", ()), MAX_BASELINES)
        ),
        str(data.get("baseline_note", NO_BASELINE)),
        tuple(
            RegisterEntry(
                row["asset_class"],
                row["dataset_id"],
                row["dataset_name"],
                int(row["count"]),
                tuple(
                    RegisterItem(item["name"], item["country"], item["precision"], item["url"])
                    for item in _rows(row.get("listed", ()), MAX_LISTED_ITEMS)
                ),
                row["as_of"],
                row["attribution"],
                row["matched_by"],
            )
            for row in _rows(data.get("coverage", ()), 2)
        ),
        readings_from_list(list(data.get("instruments", ()))),
        str(data.get("instrument_note", NO_INSTRUMENTS)),
    )
