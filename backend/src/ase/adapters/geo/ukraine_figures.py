"""Packaged confirmed-loss and civilian-harm snapshots, validated once at load."""

from __future__ import annotations

import json
from datetime import date, datetime
from functools import lru_cache
from importlib.resources import files
from typing import Any

from ase.domain.ukraine.confirmed import (
    CasualtyReference,
    CivilianHarm,
    CivilianHarmMonth,
    ConfirmedLosses,
    LossDay,
    LossRow,
)
from ase.domain.ukraine.reference import Side

LOSSES_RESOURCE = "ukraine_losses.json"
CASUALTIES_RESOURCE = "ukraine_casualties.json"
BASES = frozenset({"claimed", "assessed", "visually_confirmed", "documented", "reported"})


def _text(value: Any, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Snapshot text field missing or too long")
    return value.strip()


def _count(value: Any) -> int:
    number = int(value)
    if number < 0:
        raise ValueError("Snapshot count cannot be negative")
    return number


def _optional_count(value: Any) -> int | None:
    return None if value is None else _count(value)


def parse_losses(raw: dict[str, Any]) -> ConfirmedLosses:
    return ConfirmedLosses(
        recorded_on=date.fromisoformat(_text(raw.get("recorded_on"), 10)),
        retrieved_at=datetime.fromisoformat(_text(raw.get("retrieved_at"), 40)),
        attribution=_text(raw.get("attribution"), 300),
        licence=_text(raw.get("licence"), 120),
        source_url=_text(raw.get("source_url"), 300),
        rows=tuple(
            LossRow(
                side=Side(_text(item.get("side"), 2)),
                equipment_type=_text(item.get("equipment_type"), 80),
                group=_text(item.get("group"), 40),
                destroyed=_count(item.get("destroyed")),
                damaged=_count(item.get("damaged")),
                abandoned=_count(item.get("abandoned")),
                captured=_count(item.get("captured")),
            )
            for item in raw.get("rows") or []
        ),
        days=tuple(
            LossDay(
                on=date.fromisoformat(_text(item.get("on"), 10)),
                side=Side(_text(item.get("side"), 2)),
                total=_count(item.get("total")),
            )
            for item in raw.get("days") or []
        ),
    )


def parse_casualties(raw: dict[str, Any]) -> CivilianHarm:
    references: list[CasualtyReference] = []
    for item in raw.get("references") or []:
        basis = _text(item.get("basis"), 20)
        if basis not in BASES:
            raise ValueError("Casualty reference basis unknown")
        url = _text(item.get("url"), 600)
        if not url.startswith("https://"):
            raise ValueError("Casualty reference links must be https")
        references.append(
            CasualtyReference(
                id=_text(item.get("id"), 60),
                label=_text(item.get("label"), 160),
                text=_text(item.get("text"), 600),
                basis=basis,
                url=url,
                as_of=date.fromisoformat(_text(item.get("as_of"), 10)),
            )
        )
    return CivilianHarm(
        retrieved_at=datetime.fromisoformat(_text(raw.get("retrieved_at"), 40)),
        source_url=_text(raw.get("source_url"), 300),
        attribution=_text(raw.get("attribution"), 300),
        months=tuple(
            CivilianHarmMonth(
                month=date.fromisoformat(_text(item.get("month"), 10)),
                title=_text(item.get("title"), 160),
                url=_text(item.get("url"), 600),
                published_on=(
                    date.fromisoformat(_text(item["published_on"], 10))
                    if item.get("published_on")
                    else None
                ),
                killed=_optional_count(item.get("killed")),
                injured=_optional_count(item.get("injured")),
            )
            for item in raw.get("months") or []
        ),
        references=tuple(references),
    )


def _read(name: str) -> dict[str, Any] | None:
    resource = files("ase.resources").joinpath(name)
    if not resource.is_file():
        return None
    payload: dict[str, Any] = json.loads(resource.read_text(encoding="utf-8"))
    return payload


@lru_cache(maxsize=1)
def load_confirmed_losses() -> ConfirmedLosses | None:
    raw = _read(LOSSES_RESOURCE)
    return parse_losses(raw) if raw is not None else None


@lru_cache(maxsize=1)
def load_civilian_harm() -> CivilianHarm | None:
    raw = _read(CASUALTIES_RESOURCE)
    return parse_casualties(raw) if raw is not None else None
