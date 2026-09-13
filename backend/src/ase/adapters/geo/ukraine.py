"""Packaged Ukraine snapshots, validated once at load; absent files leave the page honest."""

from __future__ import annotations

import json
from datetime import date, datetime
from functools import lru_cache
from importlib.resources import files
from typing import Any

from ase.domain.ukraine.control import (
    MAX_NAME,
    MAX_OUTLINE_VERTICES,
    MAX_OUTLINES,
    ControlArea,
    ControlChange,
    ControlSnapshot,
    ControlStatus,
    NamedOutline,
    OblastControl,
    Polygon,
    SettlementControl,
)

CONTROL_RESOURCE = "ukraine_control.json"
OBLASTS_RESOURCE = "ukraine_oblasts.json"


def _text(value: Any, limit: int = MAX_NAME) -> str:
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError("Snapshot text field missing or too long")
    return value


def _status(value: Any) -> ControlStatus:
    if not isinstance(value, str):
        raise ValueError("Snapshot status must be text")
    return ControlStatus(value)


def _polygons(value: Any) -> tuple[Polygon, ...]:
    if not isinstance(value, list):
        raise ValueError("Snapshot polygons must be a list")
    polygons: list[Polygon] = []
    for polygon in value:
        rings: list[tuple[tuple[float, float], ...]] = []
        for ring in polygon:
            points = tuple((float(x), float(y)) for x, y in ring)
            if any(not -180 <= x <= 180 or not -90 <= y <= 90 for x, y in points):
                raise ValueError("Snapshot coordinate out of range")
            rings.append(points)
        polygons.append(tuple(rings))
    return tuple(polygons)


def _settlement(row: Any) -> SettlementControl:
    if not isinstance(row, list) or len(row) != 8:
        raise ValueError("Snapshot settlement row malformed")
    place_id, name, oblast, lat, lon, status, since, votes = row
    if not -90 <= float(lat) <= 90 or not -180 <= float(lon) <= 180:
        raise ValueError("Snapshot settlement out of range")
    if not isinstance(votes, list) or len(votes) != 4:
        raise ValueError("Snapshot settlement votes malformed")
    parsed_votes = tuple(_status(vote) for vote in votes)
    return SettlementControl(
        geoname_id=int(place_id),
        name=_text(name),
        oblast=_text(oblast),
        lat=float(lat),
        lon=float(lon),
        status=_status(status),
        since=date.fromisoformat(since) if since is not None else None,
        votes=(parsed_votes[0], parsed_votes[1], parsed_votes[2], parsed_votes[3]),
    )


def parse_control(raw: dict[str, Any]) -> ControlSnapshot:
    return ControlSnapshot(
        assessment_date=date.fromisoformat(_text(raw.get("assessment_date"), 10)),
        release_stamp=_text(raw.get("release_stamp"), 40),
        retrieved_at=datetime.fromisoformat(_text(raw.get("retrieved_at"), 40)),
        attribution=_text(raw.get("attribution"), 400),
        licence=_text(raw.get("licence"), 40),
        source_url=_text(raw.get("source_url"), 200),
        method_note=_text(raw.get("method_note"), 600),
        places_total=int(raw.get("places_total") or 0),
        settlements=tuple(_settlement(row) for row in raw.get("settlements") or []),
        areas=tuple(
            ControlArea(
                status=_status(item.get("status")), polygons=_polygons(item.get("polygons"))
            )
            for item in raw.get("areas") or []
        ),
        oblasts=tuple(
            OblastControl(
                name=_text(item.get("name")),
                total=int(item.get("total") or 0),
                ua=int(item.get("ua") or 0),
                ru=int(item.get("ru") or 0),
                contested=int(item.get("contested") or 0),
                unknown=int(item.get("unknown") or 0),
            )
            for item in raw.get("oblasts") or []
        ),
        changes=tuple(
            ControlChange(
                geoname_id=int(item.get("geoname_id") or 0),
                name=_text(item.get("name")),
                oblast=_text(item.get("oblast")),
                previous=_status(item.get("previous")),
                status=_status(item.get("status")),
                changed_on=date.fromisoformat(_text(item.get("changed_on"), 10)),
            )
            for item in raw.get("changes") or []
        ),
    )


def parse_outlines(raw: dict[str, Any]) -> tuple[NamedOutline, ...]:
    items = raw.get("outlines")
    if not isinstance(items, list) or not 0 < len(items) <= MAX_OUTLINES:
        raise ValueError("Outline count outside the bound")
    outlines = tuple(
        NamedOutline(
            name=_text(item.get("name")),
            iso=_text(item.get("iso"), 8),
            polygons=_polygons(item.get("polygons")),
        )
        for item in items
    )
    if sum(outline.vertices for outline in outlines) > MAX_OUTLINE_VERTICES:
        raise ValueError("Outlines exceed the vertex bound")
    return outlines


def _read(name: str) -> dict[str, Any] | None:
    resource = files("ase.resources").joinpath(name)
    if not resource.is_file():
        return None
    payload: dict[str, Any] = json.loads(resource.read_text(encoding="utf-8"))
    return payload


@lru_cache(maxsize=1)
def load_control_snapshot() -> ControlSnapshot | None:
    raw = _read(CONTROL_RESOURCE)
    return parse_control(raw) if raw is not None else None


@lru_cache(maxsize=1)
def load_oblast_outlines() -> tuple[NamedOutline, ...]:
    raw = _read(OBLASTS_RESOURCE)
    return parse_outlines(raw) if raw is not None else ()
