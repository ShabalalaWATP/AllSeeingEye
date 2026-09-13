"""Packaged office-holder roster, validated once at load; never a user-supplied path."""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from importlib.resources import files
from typing import Any, get_args

from ase.domain.public_figures import (
    MAX_ALIASES,
    MAX_FIGURES,
    MAX_NAME_LENGTH,
    FigurePortrait,
    FigureRole,
    PublicFigure,
    PublicFigureCatalogue,
)

MAX_PORTRAIT_BASE64 = 24_000
ROLES = frozenset(get_args(FigureRole))


def _text(value: Any, limit: int = MAX_NAME_LENGTH) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Roster text field missing or too long")
    return value.strip()


def _portrait(value: Any) -> FigurePortrait | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Roster portrait must be an object")
    png = _text(value.get("png_base64"), MAX_PORTRAIT_BASE64)
    if not all(c.isalnum() or c in "+/=" for c in png):
        raise ValueError("Roster portrait is not base64")
    return FigurePortrait(
        png_base64=png,
        licence=_text(value.get("licence"), 80),
        credit=_text(value.get("credit"), 300),
        source_url=_text(value.get("source_url"), 600),
    )


def parse_figure(raw: dict[str, Any]) -> PublicFigure:
    role: FigureRole | None = raw.get("role") if raw.get("role") in ROLES else None
    if role is None:
        raise ValueError("Roster role unknown")
    seat = raw.get("seat") or {}
    lat, lon = float(seat.get("lat") or 0.0), float(seat.get("lon") or 0.0)
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Roster seat out of range")
    country = raw.get("country_iso")
    if country is not None and not (isinstance(country, str) and len(country) == 2):
        raise ValueError("Roster country must be ISO alpha-2")
    aliases = raw.get("aliases") or []
    if not isinstance(aliases, list) or len(aliases) > MAX_ALIASES:
        raise ValueError("Roster aliases exceed the bound")
    organisation = raw.get("organisation")
    return PublicFigure(
        id=_text(raw.get("id"), 40),
        wikidata_id=_text(raw.get("wikidata_id"), 20),
        name=_text(raw.get("name")),
        office=_text(raw.get("office")),
        role=role,
        country_iso=country,
        organisation=_text(organisation, 80) if organisation is not None else None,
        aliases=tuple(_text(alias) for alias in aliases),
        seat_name=_text(seat.get("name")),
        seat_lat=lat,
        seat_lon=lon,
        portrait=_portrait(raw.get("portrait")),
    )


def parse_catalogue(raw: dict[str, Any]) -> PublicFigureCatalogue:
    figures = raw.get("figures")
    if not isinstance(figures, list) or not 0 < len(figures) <= MAX_FIGURES:
        raise ValueError("Roster size outside the bound")
    parsed = tuple(parse_figure(item) for item in figures)
    if len({figure.id for figure in parsed}) != len(parsed):
        raise ValueError("Roster ids must be unique")
    return PublicFigureCatalogue(
        retrieved_at=datetime.fromisoformat(_text(raw.get("retrieved_at"), 40)),
        source_note=_text(raw.get("source"), 300),
        figures=parsed,
    )


@lru_cache(maxsize=1)
def load_public_figures() -> PublicFigureCatalogue:
    text = files("ase.resources").joinpath("public_figures.json").read_text(encoding="utf-8")
    return parse_catalogue(json.loads(text))
