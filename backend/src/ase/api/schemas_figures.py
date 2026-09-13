"""Public figures contract: a roster with reporting-derived placements and explicit bases."""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field

from ase.api.schemas_events import EventOut
from ase.application.public_figures import FigureBoard, FigureCard
from ase.domain.public_figures import FigureRole, PlacementBasis


class FigurePortraitOut(BaseModel):
    png_base64: str = Field(max_length=24_000)
    licence: str
    credit: str
    source_url: str


class FigurePlacementOut(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    basis: PlacementBasis
    detail: str
    event_id: str | None
    published_at: datetime | None


class FigureOut(BaseModel):
    id: str
    wikidata_id: str
    name: str
    office: str
    role: FigureRole
    country_iso: str | None
    organisation: str | None
    seat_name: str
    portrait: FigurePortraitOut | None
    placement: FigurePlacementOut
    mentions: int = Field(ge=0)
    latest: list[EventOut] = Field(max_length=5)

    @classmethod
    def from_card(cls, card: FigureCard) -> Self:
        figure, placement = card.figure, card.placement
        portrait = figure.portrait
        return cls(
            id=figure.id,
            wikidata_id=figure.wikidata_id,
            name=figure.name,
            office=figure.office,
            role=figure.role,
            country_iso=figure.country_iso,
            organisation=figure.organisation,
            seat_name=figure.seat_name,
            portrait=(
                FigurePortraitOut(
                    png_base64=portrait.png_base64,
                    licence=portrait.licence,
                    credit=portrait.credit,
                    source_url=portrait.source_url,
                )
                if portrait
                else None
            ),
            placement=FigurePlacementOut(
                latitude=placement.lat,
                longitude=placement.lon,
                basis=placement.basis,
                detail=placement.detail,
                event_id=placement.event_id,
                published_at=placement.published_at,
            ),
            mentions=card.mentions,
            latest=[EventOut.from_event(event) for event in card.latest],
        )


class FigureBoardOut(BaseModel):
    figures: list[FigureOut] = Field(max_length=80)
    window_hours: int
    events_scanned: int
    roster_retrieved_at: datetime
    source_note: str
    generated_at: datetime
    caveat: str

    @classmethod
    def from_board(cls, board: FigureBoard) -> Self:
        return cls(
            figures=[FigureOut.from_card(card) for card in board.cards],
            window_hours=board.window_hours,
            events_scanned=board.events_scanned,
            roster_retrieved_at=board.roster_retrieved_at,
            source_note=board.source_note,
            generated_at=board.generated_at,
            caveat=(
                "Markers show where public reporting names an office-holder, or the seat of "
                "office when nothing located names them. Neither is confirmed presence, and "
                "absence of reporting never means an official is at home."
            ),
        )
