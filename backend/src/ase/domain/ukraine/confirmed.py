"""Visually confirmed losses (Oryx) and documented civilian harm (HRMMU), kept apart from claims."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType

from ase.domain.ukraine.reference import Side

MAX_LOSS_ROWS = 120
MAX_LOSS_DAYS = 62
MAX_HARM_MONTHS = 36
MAX_REFERENCES = 12

# Oryx type names to the equipment specialities on the page; unmapped types read "other".
LOSS_GROUPS: Mapping[str, str] = MappingProxyType(
    {
        "Tanks": "tanks",
        "Armoured Fighting Vehicles": "ifv_apc",
        "Infantry Fighting Vehicles": "ifv_apc",
        "Armoured Personnel Carriers": "ifv_apc",
        "Mine-Resistant Ambush Protected": "ifv_apc",
        "Infantry Mobility Vehicles": "ifv_apc",
        "Command Posts And Communications Stations": "communications_ew",
        "Radars": "communications_ew",
        "Radars And Communications Equipment": "communications_ew",
        "Jammers And Deception Systems": "communications_ew",
        "Towed Artillery": "artillery",
        "Self-Propelled Artillery": "artillery",
        "Rocket and Missile Artillery": "artillery",
        "Artillery and Missile Support Vehicles And Equipment": "artillery",
        "Anti-Aircraft Guns": "air_defence",
        "Self-Propelled Anti-Aircraft Guns": "air_defence",
        "Surface-To-Air Missile Systems": "air_defence",
        "Aircraft": "aviation",
        "Helicopters": "aviation",
        "Unmanned Combat Aerial Vehicles": "drones",
        "Naval Ships": "naval",
        "Naval Ships and Submarines": "naval",
        "Self-Propelled Anti-Tank Missile Systems": "small_arms",
    }
)
TOTAL_TYPE = "All Types"


def loss_group(equipment_type: str) -> str:
    return LOSS_GROUPS.get(" ".join(equipment_type.split()), "other")


@dataclass(frozen=True, slots=True)
class LossRow:
    side: Side
    equipment_type: str
    group: str
    destroyed: int
    damaged: int
    abandoned: int
    captured: int

    @property
    def total(self) -> int:
        return self.destroyed + self.damaged + self.abandoned + self.captured


@dataclass(frozen=True, slots=True)
class LossDay:
    on: date
    side: Side
    total: int


@dataclass(frozen=True, slots=True)
class ConfirmedLosses:
    recorded_on: date
    retrieved_at: datetime
    attribution: str
    licence: str
    source_url: str
    rows: tuple[LossRow, ...]
    days: tuple[LossDay, ...]

    def __post_init__(self) -> None:
        if not 0 < len(self.rows) <= MAX_LOSS_ROWS or len(self.days) > MAX_LOSS_DAYS:
            raise ValueError("Confirmed losses outside the row or day bound")
        if any(min(r.destroyed, r.damaged, r.abandoned, r.captured) < 0 for r in self.rows):
            raise ValueError("Confirmed losses cannot be negative")

    def total(self, side: Side) -> LossRow | None:
        for row in self.rows:
            if row.side is side and row.equipment_type == TOTAL_TYPE:
                return row
        return None


@dataclass(frozen=True, slots=True)
class CivilianHarmMonth:
    month: date
    title: str
    url: str
    published_on: date | None
    killed: int | None
    injured: int | None


@dataclass(frozen=True, slots=True)
class CasualtyReference:
    """A curated count from a named body with its basis, dated; never merged with others."""

    id: str
    label: str
    text: str
    basis: str
    url: str
    as_of: date


@dataclass(frozen=True, slots=True)
class CivilianHarm:
    retrieved_at: datetime
    source_url: str
    attribution: str
    months: tuple[CivilianHarmMonth, ...]
    references: tuple[CasualtyReference, ...]

    def __post_init__(self) -> None:
        if len(self.months) > MAX_HARM_MONTHS or len(self.references) > MAX_REFERENCES:
            raise ValueError("Civilian harm outside the month or reference bound")
        for month in self.months:
            counts = (month.killed, month.injured)
            if any(count is not None and count < 0 for count in counts):
                raise ValueError("Civilian harm counts cannot be negative")

    @property
    def latest(self) -> CivilianHarmMonth | None:
        counted = [m for m in self.months if m.killed is not None]
        return max(counted, key=lambda m: m.month) if counted else None
