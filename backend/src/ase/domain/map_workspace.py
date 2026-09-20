"""Bounded user-authored map artefacts, independent of collected observations."""

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from ase.domain.map_workspace_radio import validate_radio

WorkspaceKind = Literal["drawings", "radio"]
MAX_DOCUMENT_BYTES = 128 * 1024
MAX_SCOPE_DOCUMENTS = 100


@dataclass(frozen=True, slots=True)
class MapWorkspaceDocument:
    id: UUID
    kind: WorkspaceKind
    title: str
    payload: dict[str, Any]
    revision: int
    created_by: UUID
    team_id: UUID | None
    created_at: datetime
    updated_at: datetime


def validate_payload(kind: WorkspaceKind, payload: dict[str, Any]) -> None:
    """Bound traversal before encoding; reject non-JSON and non-finite values."""
    _bounded_json(payload)
    if kind == "drawings":
        _drawings(payload)
    elif kind == "radio":
        validate_radio(payload)
    else:
        raise ValueError("Unsupported map document kind.")


def _bounded_json(payload: dict[str, Any]) -> None:
    pending: list[tuple[object, int]] = [(payload, 0)]
    count = 0
    while pending:
        value, depth = pending.pop()
        count += 1
        if count > 10000 or depth > 12:
            raise ValueError("Map document is too complex.")
        if isinstance(value, dict):
            if len(value) > 1000 or any(not isinstance(key, str) for key in value):
                raise ValueError("Invalid map document keys.")
            pending.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            if len(value) > 2000:
                raise ValueError("Map document list is too long.")
            pending.extend((item, depth + 1) for item in value)
        elif isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("Map document numbers must be finite.")
        elif value is not None and type(value) not in (str, int, bool):
            raise ValueError("Map documents must contain JSON values only.")
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise ValueError("Map document exceeds 128 KiB.")


def _drawings(payload: dict[str, Any]) -> None:
    if (
        set(payload) - {"version", "objects", "selectedId"}
        or type(payload.get("version")) is not int
        or payload["version"] != 1
    ):
        raise ValueError("Unsupported drawing document.")
    objects = payload.get("objects")
    if not isinstance(objects, list) or len(objects) > 50:
        raise ValueError("Drawing documents support up to 50 objects.")
    ids: set[str] = set()
    for item in objects:
        if not isinstance(item, dict) or set(item) - {
            "id",
            "name",
            "shape",
            "anchors",
            "colour",
            "visible",
            "locked",
            "notes",
        }:
            raise ValueError("Invalid drawing object.")
        identity = item.get("id")
        if not isinstance(identity, str) or not identity or len(identity) > 100 or identity in ids:
            raise ValueError("Drawing object IDs must be unique and bounded.")
        ids.add(identity)
        _drawing_fields(item)
    if payload.get("selectedId") is not None and payload["selectedId"] not in ids:
        raise ValueError("The selected drawing does not exist.")


def _drawing_fields(item: dict[str, Any]) -> None:
    for key, limit in (("name", 200), ("notes", 2000)):
        if not isinstance(item.get(key), str) or len(item[key]) > limit:
            raise ValueError(f"Invalid drawing {key}.")
    if item.get("shape") not in {"point", "path", "polygon", "rectangle", "circle"}:
        raise ValueError("Invalid drawing shape.")
    if not isinstance(item.get("colour"), str) or not re.fullmatch(
        r"#[0-9a-fA-F]{6}", item["colour"]
    ):
        raise ValueError("Invalid drawing colour.")
    if any(type(item.get(key)) is not bool for key in ("visible", "locked")):
        raise ValueError("Invalid drawing visibility or lock.")
    anchors = item.get("anchors")
    if not isinstance(anchors, list) or len(anchors) > 32:
        raise ValueError("Drawing objects support up to 32 anchors.")
    for point in anchors:
        if (
            not isinstance(point, list)
            or len(point) != 2
            or any(type(value) not in (int, float) for value in point)
            or not -180 <= point[0] <= 180
            or not -90 <= point[1] <= 90
        ):
            raise ValueError("Drawing coordinates must be longitude, latitude.")
