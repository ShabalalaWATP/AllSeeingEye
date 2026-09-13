"""Public figures board: roster plus what retained reporting says about each office-holder."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from ase.application.ports import Clock
from ase.application.ports.feeds import EventQuery, EventStore
from ase.domain.events import Category, Event
from ase.domain.public_figures import (
    FigurePlacement,
    PublicFigure,
    PublicFigureCatalogue,
    match_people,
    place_figure,
)

WINDOW = timedelta(hours=72)
POOL = 3_000
LATEST = 5
CATEGORIES = frozenset({Category.NEWS, Category.POLITICAL, Category.CONFLICT})


@dataclass(frozen=True, slots=True)
class FigureCard:
    figure: PublicFigure
    placement: FigurePlacement
    mentions: int
    latest: tuple[Event, ...]


@dataclass(frozen=True, slots=True)
class FigureBoard:
    cards: tuple[FigureCard, ...]
    window_hours: int
    events_scanned: int
    roster_retrieved_at: datetime
    source_note: str
    generated_at: datetime


class PublicFigureService:
    def __init__(self, store: EventStore, clock: Clock, catalogue: PublicFigureCatalogue) -> None:
        self._store = store
        self._clock = clock
        self._catalogue = catalogue

    @property
    def catalogue(self) -> PublicFigureCatalogue:
        return self._catalogue

    def board(self) -> FigureBoard:
        now = self._clock.now()
        # Official Atom feeds declare modification dates only, so their items have no
        # publication instant; keep them while they were collected inside the window.
        events = [
            event
            for event in self._store.query(
                EventQuery(
                    categories=CATEGORIES,
                    since=now - WINDOW,
                    limit=POOL,
                    include_unknown_dates=True,
                )
            )
            if event.published_at is not None or event.observed_at >= now - WINDOW
        ]
        by_person: dict[str, list[Event]] = defaultdict(list)
        figures = self._catalogue.figures
        for event in sorted(events, key=_recency, reverse=True):
            text = " ".join(part for part in (event.title, event.title_en, event.summary) if part)
            for person_id in match_people(text, figures):
                by_person[person_id].append(event)
        cards = tuple(
            FigureCard(
                figure=figure,
                placement=place_figure(figure, tuple(by_person.get(figure.wikidata_id, ()))),
                mentions=len(by_person.get(figure.wikidata_id, ())),
                latest=tuple(by_person.get(figure.wikidata_id, ())[:LATEST]),
            )
            for figure in figures
        )
        return FigureBoard(
            cards=cards,
            window_hours=int(WINDOW.total_seconds() // 3600),
            events_scanned=len(events),
            roster_retrieved_at=self._catalogue.retrieved_at,
            source_note=self._catalogue.source_note,
            generated_at=now,
        )


def _recency(event: Event) -> datetime:
    return event.published_at or event.observed_at
