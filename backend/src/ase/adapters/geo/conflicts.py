"""The curated conflict list, packaged as a resource (docs/04 section 5.1)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from importlib import resources
from typing import Any

from ase.domain.events import BoundingBox
from ase.domain.trackers import Conflict

RESOURCE = "conflicts.json"
STATUSES = ("war", "tension")


def _conflict(raw: dict[str, Any]) -> Conflict:
    conflict_id = str(raw.get("id", ""))
    if not conflict_id:
        raise ValueError("A conflict has no id")
    try:
        west, south, east, north = (float(value) for value in raw["bbox"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Conflict {conflict_id} has no usable bounding box") from exc
    if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= north <= 90):
        raise ValueError(f"Conflict {conflict_id} has a bounding box out of range")
    status = str(raw.get("status", "war"))
    if status not in STATUSES:
        raise ValueError(f"Conflict {conflict_id} has an unknown status {status!r}")
    return Conflict(
        id=conflict_id,
        name=str(raw.get("name", conflict_id)),
        status=status,
        countries=tuple(str(code).upper() for code in raw.get("countries", [])),
        bbox=BoundingBox(west=west, south=south, east=east, north=north),
        belligerents=tuple(str(item) for item in raw.get("belligerents", [])),
        keywords=tuple(str(item) for item in raw.get("keywords", [])),
        summary=str(raw.get("summary", "")),
    )


class ConflictIndex:
    def __init__(self, conflicts: Sequence[Conflict]) -> None:
        self._by_id = {conflict.id: conflict for conflict in conflicts}
        if len(self._by_id) != len(conflicts):
            raise ValueError("Duplicate conflict ids")

    @classmethod
    def from_resource(cls) -> ConflictIndex:
        text = resources.files("ase.resources").joinpath(RESOURCE).read_text(encoding="utf-8")
        data = json.loads(text)
        return cls([_conflict(item) for item in data["conflicts"]])

    def all(self) -> Sequence[Conflict]:
        return tuple(self._by_id.values())

    def get(self, conflict_id: str) -> Conflict | None:
        return self._by_id.get(conflict_id)
