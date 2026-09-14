"""Provider frontline and spotted-loss contracts: reported geometry with its status and terms."""

from __future__ import annotations

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel, Field

from ase.domain.ukraine.frontline import (
    FrontlineKind,
    FrontlineState,
    FrontlineStatus,
    SpottedState,
)

Polygons = list[list[list[list[float]]]]
Lines = list[list[list[float]]]


class FrontlineFeatureOut(BaseModel):
    kind: FrontlineKind
    label: str
    polygons: Polygons
    lines: Lines


class FrontlineOut(BaseModel):
    status: FrontlineStatus
    reason: str
    provider: str | None
    attribution: str | None
    terms: str | None
    assessed_at: str | None
    downloaded_at: datetime | None
    features: list[FrontlineFeatureOut]

    @classmethod
    def from_state(cls, state: FrontlineState) -> Self:
        snapshot = state.snapshot
        return cls(
            status=state.status,
            reason=state.reason,
            provider=snapshot.provider if snapshot else None,
            attribution=snapshot.attribution if snapshot else None,
            terms=snapshot.terms if snapshot else None,
            assessed_at=snapshot.assessed_at if snapshot else None,
            downloaded_at=snapshot.downloaded_at if snapshot else None,
            features=[
                FrontlineFeatureOut(
                    kind=feature.kind,
                    label=feature.label,
                    polygons=[
                        [[[x, y] for x, y in ring] for ring in polygon]
                        for polygon in feature.polygons
                    ],
                    lines=[[[x, y] for x, y in line] for line in feature.lines],
                )
                for feature in (snapshot.features if snapshot else ())
            ],
        )


class SpottedLossOut(BaseModel):
    id: int
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    model: str
    equipment_type: str
    status: str
    lost_by: str
    on: date
    place: str


class SpottedOut(BaseModel):
    status: FrontlineStatus
    reason: str
    attribution: str
    downloaded_at: datetime | None
    losses: list[SpottedLossOut]

    @classmethod
    def from_state(cls, state: SpottedState) -> Self:
        return cls(
            status=state.status,
            reason=state.reason,
            attribution=state.attribution,
            downloaded_at=state.downloaded_at,
            losses=[
                SpottedLossOut(
                    id=loss.id,
                    lat=loss.lat,
                    lon=loss.lon,
                    model=loss.model,
                    equipment_type=loss.equipment_type,
                    status=loss.status,
                    lost_by=loss.lost_by,
                    on=loss.on,
                    place=loss.place,
                )
                for loss in state.losses
            ],
        )
