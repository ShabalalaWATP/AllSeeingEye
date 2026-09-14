"""Ukraine war tracker contract: reported control, claimed figures and grouped updates."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, Field

from ase.api.schemas_events import EventOut
from ase.api.schemas_ukraine_losses import CivilianHarmOut, ConfirmedLossesOut, LensSeriesOut
from ase.application.ukraine import UkraineBoard, UpdateEntry
from ase.domain.ukraine.control import ControlSnapshot, ControlStatus, NamedOutline
from ase.domain.ukraine.lenses import Lens
from ase.domain.ukraine.losses import HEADLINE_CATEGORIES, LOSS_CATEGORIES, ClaimedLosses
from ase.domain.ukraine.updates import UpdateGroup

Polygons = list[list[list[list[float]]]]


class ClaimedLossesOut(BaseModel):
    reported_on: date
    day: int = Field(ge=1)
    source_url: str | None
    totals: dict[str, int]
    increase: dict[str, int]

    @classmethod
    def from_claim(cls, claim: ClaimedLosses) -> Self:
        return cls(
            reported_on=claim.reported_on,
            day=claim.day,
            source_url=claim.source_url,
            totals=dict(claim.totals),
            increase=dict(claim.increase),
        )


class UpdateOut(BaseModel):
    event: EventOut
    group: UpdateGroup
    lenses: list[Lens]

    @classmethod
    def from_entry(cls, entry: UpdateEntry) -> Self:
        return cls(
            event=EventOut.from_event(entry.event),
            group=entry.group,
            lenses=sorted(entry.lenses),
        )


class OblastControlOut(BaseModel):
    name: str
    total: int = Field(ge=0)
    ua: int = Field(ge=0)
    ru: int = Field(ge=0)
    contested: int = Field(ge=0)
    unknown: int = Field(ge=0)


class ControlChangeOut(BaseModel):
    geoname_id: int
    name: str
    oblast: str
    previous: ControlStatus
    status: ControlStatus
    changed_on: date


class ControlSummaryOut(BaseModel):
    assessment_date: date
    release_stamp: str
    retrieved_at: datetime
    attribution: str
    licence: str
    source_url: str
    method_note: str
    places_total: int = Field(ge=0)
    retained: int = Field(ge=0)
    counts: dict[str, int]
    oblasts: list[OblastControlOut]
    changes: list[ControlChangeOut]

    @classmethod
    def from_snapshot(cls, snapshot: ControlSnapshot) -> Self:
        return cls(
            assessment_date=snapshot.assessment_date,
            release_stamp=snapshot.release_stamp,
            retrieved_at=snapshot.retrieved_at,
            attribution=snapshot.attribution,
            licence=snapshot.licence,
            source_url=snapshot.source_url,
            method_note=snapshot.method_note,
            places_total=snapshot.places_total,
            retained=len(snapshot.settlements),
            counts={status.value: snapshot.count(status) for status in ControlStatus},
            oblasts=[
                OblastControlOut(
                    name=o.name,
                    total=o.total,
                    ua=o.ua,
                    ru=o.ru,
                    contested=o.contested,
                    unknown=o.unknown,
                )
                for o in snapshot.oblasts
            ],
            changes=[
                ControlChangeOut(
                    geoname_id=c.geoname_id,
                    name=c.name,
                    oblast=c.oblast,
                    previous=c.previous,
                    status=c.status,
                    changed_on=c.changed_on,
                )
                for c in snapshot.changes
            ],
        )


class FreshnessOut(BaseModel):
    control_assessed: date | None
    assessment_published: datetime | None
    claim_reported: date | None
    latest_update: datetime | None


class UkraineBoardOut(BaseModel):
    generated_at: datetime
    day_number: int = Field(ge=1)
    day_basis: Literal["claimed", "computed"]
    window_days: int = Field(ge=1)
    events_scanned: int = Field(ge=0)
    updates: list[UpdateOut]
    lens_counts: dict[str, int]
    claims: list[ClaimedLossesOut]
    categories: dict[str, str]
    headline_categories: list[str]
    control: ControlSummaryOut | None
    freshness: FreshnessOut
    confirmed: ConfirmedLossesOut | None
    civilian_harm: CivilianHarmOut | None
    lens_series: list[LensSeriesOut]

    @classmethod
    def from_board(cls, board: UkraineBoard) -> Self:
        freshness = board.freshness
        return cls(
            generated_at=board.generated_at,
            day_number=board.day_number,
            day_basis=board.day_basis,
            window_days=board.window_days,
            events_scanned=board.events_scanned,
            updates=[UpdateOut.from_entry(entry) for entry in board.updates],
            lens_counts={lens.value: count for lens, count in sorted(board.lens_counts.items())},
            claims=[ClaimedLossesOut.from_claim(claim) for claim in board.claims],
            categories=dict(LOSS_CATEGORIES),
            headline_categories=list(HEADLINE_CATEGORIES),
            control=ControlSummaryOut.from_snapshot(board.control) if board.control else None,
            confirmed=(
                ConfirmedLossesOut.from_snapshot(board.confirmed) if board.confirmed else None
            ),
            civilian_harm=(
                CivilianHarmOut.from_snapshot(board.civilian_harm) if board.civilian_harm else None
            ),
            lens_series=[LensSeriesOut.from_series(series) for series in board.lens_series],
            freshness=FreshnessOut(
                control_assessed=freshness.control_assessed,
                assessment_published=freshness.assessment_published,
                claim_reported=freshness.claim_reported,
                latest_update=freshness.latest_update,
            ),
        )


class SettlementOut(BaseModel):
    geoname_id: int
    name: str
    oblast: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    status: ControlStatus
    since: date | None
    votes: list[ControlStatus] = Field(min_length=4, max_length=4)


class AreaOut(BaseModel):
    status: ControlStatus
    polygons: Polygons


class OutlineOut(BaseModel):
    name: str
    iso: str
    polygons: Polygons


class ControlOut(BaseModel):
    summary: ControlSummaryOut | None
    settlements: list[SettlementOut]
    areas: list[AreaOut]
    outlines: list[OutlineOut]

    @classmethod
    def build(cls, snapshot: ControlSnapshot | None, outlines: tuple[NamedOutline, ...]) -> Self:
        return cls(
            summary=ControlSummaryOut.from_snapshot(snapshot) if snapshot else None,
            settlements=[
                SettlementOut(
                    geoname_id=s.geoname_id,
                    name=s.name,
                    oblast=s.oblast,
                    lat=s.lat,
                    lon=s.lon,
                    status=s.status,
                    since=s.since,
                    votes=list(s.votes),
                )
                for s in (snapshot.settlements if snapshot else ())
            ],
            areas=[
                AreaOut(status=area.status, polygons=_polygons(area.polygons))
                for area in (snapshot.areas if snapshot else ())
            ],
            outlines=[
                OutlineOut(name=o.name, iso=o.iso, polygons=_polygons(o.polygons)) for o in outlines
            ],
        )


def _polygons(polygons: tuple[tuple[tuple[tuple[float, float], ...], ...], ...]) -> Polygons:
    return [[[[x, y] for x, y in ring] for ring in polygon] for polygon in polygons]
