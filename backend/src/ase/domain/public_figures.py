"""Public office-holders and where reporting places them; a mention is never confirmed presence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from functools import lru_cache
from typing import Literal

from ase.domain.events import Event, GeoConfidence

MAX_FIGURES = 120
MAX_ALIASES = 12
MAX_NAME_LENGTH = 120
MAX_MENTION_TEXT = 4_000
MIN_SURNAME_LENGTH = 5
MIN_ALIAS_LENGTH = 10
PLACE_CONFIDENCE = frozenset({GeoConfidence.EXACT, GeoConfidence.CITY, GeoConfidence.ADMIN1})
# Title words never identify a person on their own.
TITLE_WORDS = frozenset(
    {
        "his",
        "her",
        "majesty",
        "the",
        "king",
        "queen",
        "president",
        "prime",
        "minister",
        "premier",
        "general",
        "chancellor",
        "emperor",
        "ayatollah",
        "secretary",
        "mister",
        "sir",
    }
)
# Surnames shared with many public people, or that are really given names.
GENERIC_SURNAMES = frozenset(
    {
        "silva",
        "costa",
        "saud",
        "sharif",
        "alexander",
        "charles",
        "salman",
        "haakon",
        "gustaf",
        "mahmood",
        "zheng",
    }
)

FigureRole = Literal[
    "head_of_state",
    "head_of_government",
    "head_of_state_and_government",
    "senior_official",
    "organisation",
]


class PlacementBasis(StrEnum):
    REPORTED_PLACE = "reported_place"
    REPORTED_COUNTRY = "reported_country"
    SEAT = "seat"


@dataclass(frozen=True, slots=True)
class FigurePortrait:
    png_base64: str
    licence: str
    credit: str
    source_url: str


@dataclass(frozen=True, slots=True)
class PublicFigure:
    id: str
    wikidata_id: str
    name: str
    office: str
    role: FigureRole
    country_iso: str | None
    organisation: str | None
    aliases: tuple[str, ...]
    seat_name: str
    seat_lat: float
    seat_lon: float
    portrait: FigurePortrait | None


@dataclass(frozen=True, slots=True)
class PublicFigureCatalogue:
    retrieved_at: datetime
    source_note: str
    figures: tuple[PublicFigure, ...]


@dataclass(frozen=True, slots=True)
class FigurePlacement:
    lat: float
    lon: float
    basis: PlacementBasis
    detail: str
    event_id: str | None
    published_at: datetime | None


def _distinctive_surname(name: str) -> str | None:
    """Last token of the personal name, without any trailing ' of <realm>' suffix."""
    tokens = re.split(r"\s+of\s+", name, maxsplit=1)[0].split()
    surname = tokens[-1] if len(tokens) >= 2 else ""
    folded = surname.casefold()
    if (
        len(surname) >= MIN_SURNAME_LENGTH
        and surname.isalpha()
        and folded not in TITLE_WORDS
        and folded not in GENERIC_SURNAMES
    ):
        return surname
    return None


def _usable_alias(alias: str) -> bool:
    """Multi-word aliases only, with at least one non-title word long enough to identify."""
    tokens = [token for token in re.split(r"[^\w]+", alias.casefold()) if token]
    return (
        MIN_ALIAS_LENGTH <= len(alias) <= MAX_NAME_LENGTH
        and len(tokens) >= 2
        and any(len(token) >= 4 and token not in TITLE_WORDS for token in tokens)
    )


@lru_cache(maxsize=4)
def _person_patterns(
    figures: tuple[PublicFigure, ...],
) -> tuple[tuple[str, str, re.Pattern[str]], ...]:
    """(person id, matched name, pattern); names shared by two people are dropped."""
    names: dict[str, set[str]] = {}
    for figure in figures[:MAX_FIGURES]:
        candidates = {figure.name}
        candidates.update(alias for alias in figure.aliases[:MAX_ALIASES] if _usable_alias(alias))
        surname = _distinctive_surname(figure.name)
        if surname:
            candidates.add(surname)
        for name in candidates:
            folded = " ".join(name.casefold().split())
            if 3 <= len(folded) <= MAX_NAME_LENGTH and any(c.isalpha() for c in folded):
                names.setdefault(folded, set()).add(figure.wikidata_id)
    return tuple(
        (next(iter(people)), name, re.compile(r"(?<!\w)" + re.escape(name) + r"(?!\w)"))
        for name, people in sorted(names.items(), key=lambda item: (-len(item[0]), item[0]))
        if len(people) == 1
    )


def match_people(text: str, figures: tuple[PublicFigure, ...]) -> dict[str, str]:
    """Person ids named in a bounded text prefix, with the name that matched.

    Denials and reported plans still count as mentions; the caller labels the basis.
    """
    folded = " ".join(text[:MAX_MENTION_TEXT].casefold().split())
    found: dict[str, str] = {}
    for person_id, name, pattern in _person_patterns(figures[:MAX_FIGURES]):
        if person_id not in found and pattern.search(folded):
            found[person_id] = name
    return found


def place_figure(figure: PublicFigure, mentions: tuple[Event, ...]) -> FigurePlacement:
    """Newest located mention wins; otherwise the seat of office, clearly labelled."""
    for event in mentions:
        if event.point is not None and event.geo_confidence in PLACE_CONFIDENCE:
            return FigurePlacement(
                event.point.lat,
                event.point.lon,
                PlacementBasis.REPORTED_PLACE,
                f"Placed by the newest geolocated report that names {figure.name}. "
                "A report's location is where the story is set, not confirmed presence.",
                event.id,
                event.published_at,
            )
    for event in mentions:
        if event.point is not None and event.geo_confidence is GeoConfidence.COUNTRY:
            return FigurePlacement(
                event.point.lat,
                event.point.lon,
                PlacementBasis.REPORTED_COUNTRY,
                f"Country context of the newest report that names {figure.name}, shown at the "
                "country reference point rather than a visited place.",
                event.id,
                event.published_at,
            )
    return FigurePlacement(
        figure.seat_lat,
        figure.seat_lon,
        PlacementBasis.SEAT,
        f"No located reporting names {figure.name} in this window, so the marker sits at the "
        f"seat of office ({figure.seat_name}). This is a default, not an observation.",
        None,
        None,
    )
