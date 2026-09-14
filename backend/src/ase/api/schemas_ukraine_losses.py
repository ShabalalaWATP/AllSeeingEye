"""Confirmed losses, civilian harm and lens series for the Ukraine board."""

from __future__ import annotations

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, Field

from ase.application.ukraine import LensSeries
from ase.domain.ukraine.confirmed import CivilianHarm, ConfirmedLosses
from ase.domain.ukraine.lenses import Lens
from ase.domain.ukraine.reference import Side


class LossRowOut(BaseModel):
    side: Side
    equipment_type: str
    group: str
    destroyed: int = Field(ge=0)
    damaged: int = Field(ge=0)
    abandoned: int = Field(ge=0)
    captured: int = Field(ge=0)
    total: int = Field(ge=0)


class LossDayOut(BaseModel):
    on: date
    side: Side
    total: int = Field(ge=0)


class ConfirmedLossesOut(BaseModel):
    recorded_on: date
    retrieved_at: datetime
    attribution: str
    licence: str
    source_url: str
    rows: list[LossRowOut]
    days: list[LossDayOut]

    @classmethod
    def from_snapshot(cls, snapshot: ConfirmedLosses) -> Self:
        return cls(
            recorded_on=snapshot.recorded_on,
            retrieved_at=snapshot.retrieved_at,
            attribution=snapshot.attribution,
            licence=snapshot.licence,
            source_url=snapshot.source_url,
            rows=[
                LossRowOut(
                    side=row.side,
                    equipment_type=row.equipment_type,
                    group=row.group,
                    destroyed=row.destroyed,
                    damaged=row.damaged,
                    abandoned=row.abandoned,
                    captured=row.captured,
                    total=row.total,
                )
                for row in snapshot.rows
            ],
            days=[LossDayOut(on=day.on, side=day.side, total=day.total) for day in snapshot.days],
        )


class CivilianHarmMonthOut(BaseModel):
    month: date
    title: str
    url: str
    published_on: date | None
    killed: int | None
    injured: int | None


class CasualtyReferenceOut(BaseModel):
    id: str
    label: str
    text: str
    basis: str
    url: str
    as_of: date


class CivilianHarmOut(BaseModel):
    retrieved_at: datetime
    source_url: str
    attribution: str
    months: list[CivilianHarmMonthOut]
    references: list[CasualtyReferenceOut]

    @classmethod
    def from_snapshot(cls, harm: CivilianHarm) -> Self:
        return cls(
            retrieved_at=harm.retrieved_at,
            source_url=harm.source_url,
            attribution=harm.attribution,
            months=[
                CivilianHarmMonthOut(
                    month=m.month,
                    title=m.title,
                    url=m.url,
                    published_on=m.published_on,
                    killed=m.killed,
                    injured=m.injured,
                )
                for m in harm.months
            ],
            references=[
                CasualtyReferenceOut(
                    id=r.id, label=r.label, text=r.text, basis=r.basis, url=r.url, as_of=r.as_of
                )
                for r in harm.references
            ],
        )


class LensSeriesOut(BaseModel):
    lens: Lens
    days: list[date]
    groups: dict[str, list[int]]

    @classmethod
    def from_series(cls, series: LensSeries) -> Self:
        return cls(
            lens=series.lens,
            days=list(series.days),
            groups={group.value: list(values) for group, values in series.groups.items()},
        )
