"""Response models for the aviation tracker board and the GNSS interference map."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel

from ase.api.schemas_events import EventOut
from ase.application.trackers.aviation import AreaActivity, AviationBoard, CountryActivity
from ase.domain.aviation import JamCell


class CountryActivityOut(BaseModel):
    iso: str
    count: int
    baseline: float | None
    ratio: float | None

    @classmethod
    def from_row(cls, row: CountryActivity) -> Self:
        return cls(iso=row.iso, count=row.count, baseline=row.baseline, ratio=row.ratio)


class AreaActivityOut(BaseModel):
    id: str
    name: str
    count: int
    military: int
    baseline: float | None

    @classmethod
    def from_row(cls, row: AreaActivity) -> Self:
        return cls(
            id=row.id, name=row.name, count=row.count, military=row.military, baseline=row.baseline
        )


class AviationBoardOut(BaseModel):
    military_total: int
    interesting: int
    ladd: int
    pia: int
    by_country: list[CountryActivityOut]
    emergencies: list[EventOut]
    areas: list[AreaActivityOut]
    jam_amber: int
    jam_red: int
    jam_updated_at: datetime | None

    @classmethod
    def from_board(cls, board: AviationBoard) -> Self:
        return cls(
            military_total=board.military_total,
            interesting=board.interesting,
            ladd=board.ladd,
            pia=board.pia,
            by_country=[CountryActivityOut.from_row(row) for row in board.by_country],
            emergencies=[EventOut.from_event(event) for event in board.emergencies],
            areas=[AreaActivityOut.from_row(row) for row in board.areas],
            jam_amber=board.jam_amber,
            jam_red=board.jam_red,
            jam_updated_at=board.jam_updated_at,
        )


class JamCellOut(BaseModel):
    lon: float
    lat: float
    size: float
    good: int
    bad: int
    percent_bad: float
    level: str

    @classmethod
    def from_cell(cls, cell: JamCell) -> Self:
        return cls(
            lon=cell.lon,
            lat=cell.lat,
            size=cell.size,
            good=cell.good,
            bad=cell.bad,
            percent_bad=cell.percent_bad,
            level=cell.level,
        )


class JamMapOut(BaseModel):
    cells: list[JamCellOut]
    updated_at: datetime | None
