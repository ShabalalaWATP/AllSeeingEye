"""Named live map views: view configuration only, never live events.

A live view stores which layers and filters were chosen, the time window, the nation
filter, the projection, the camera and an optional collection plan filter by ID.
Every identifier is checked against the known catalogue on write; a reader drops ids that
have since been retired. Raw events, geometry and model output are never accepted.
"""

import math
import re
from typing import Any, TypeGuard
from uuid import UUID

from ase.domain.events import Category

MAX_WINDOW_HOURS = 24 * 365

BASE_LAYERS = frozenset(
    {"dark", "streets", "light", "satellite", "hybrid", "os_road", "os_outdoor", "os_light"}
)
LAYER_IDS = frozenset(
    {category.value for category in Category}
    | {"aircraft", "vessels", "firms", "fires", "interference", "terminator"}
)
_TRAFFIC = frozenset({"all", "military"})
_CONFLICT_GROUPS = frozenset(
    {
        "all",
        "armed_clashes",
        "organised_violence",
        "strikes",
        "civilian_harm",
        "protests",
        "riots",
        "unrest",
        "military_activity",
        "other",
    }
)
_CYBER_KINDS = frozenset(
    {
        "all",
        "ransomware_claim",
        "outage_signal",
        "known_exploited_vulnerability",
        "advisory",
        "threat_report",
        "news_report",
        "other",
    }
)
# Each known filter id with the exact values it may take.
FILTER_CHOICES: dict[str, frozenset[Any]] = {
    "quality": frozenset({"all", "reported", "approximate", "propagated", "unplotted"}),
    "flight": _TRAFFIC,
    "vessel": _TRAFFIC,
    "gnss_level": frozenset({"all", "red"}),
    "gnss_minimum": frozenset({5, 10, 25, 50}),
    "cyber_kind": _CYBER_KINDS,
    "conflict_group": _CONFLICT_GROUPS,
    "conflict_precision": frozenset({"all", "exact", "approximate"}),
}
BOOLEAN_FILTERS = frozenset({"conflict_historical", "conflict_unreviewed"})
TEXT_FILTERS = {"cyber_query": 100}
VIEW_KEYS = frozenset(
    {
        "version",
        "projection",
        "camera",
        "base_layer",
        "layers",
        "window_hours",
        "nation",
        "filters",
        "plan_id",
    }
)
_NATION = re.compile(r"[A-Z]{2,3}")


def validate_live_view(payload: dict[str, Any]) -> None:
    if set(payload) != VIEW_KEYS or _int(payload["version"]) != 1:
        raise ValueError("Unsupported live view document.")
    if payload["projection"] not in ("globe", "map"):
        raise ValueError("Unknown map projection.")
    if payload["base_layer"] not in BASE_LAYERS:
        raise ValueError("Unknown base layer.")
    _camera(payload["camera"])
    layers = payload["layers"]
    if (
        not isinstance(layers, list)
        or len(layers) > len(LAYER_IDS)
        or any(not isinstance(layer, str) or layer not in LAYER_IDS for layer in layers)
        or len(set(layers)) != len(layers)
    ):
        raise ValueError("Live views may only name known layers, once each.")
    window = payload["window_hours"]
    if window is not None and not (_number(window) and 0 < window <= MAX_WINDOW_HOURS):
        raise ValueError("The time window must be a positive number of hours or null.")
    nation = payload["nation"]
    if nation is not None and not (isinstance(nation, str) and _NATION.fullmatch(nation)):
        raise ValueError("The nation filter must be an upper-case ISO country code.")
    _filters(payload["filters"])
    if payload["plan_id"] is not None:
        _uuid(payload["plan_id"])


def view_plan(payload: dict[str, Any]) -> UUID | None:
    """The collection plan filter named by a validated live view."""
    plan = payload.get("plan_id")
    return UUID(plan) if plan else None


def _camera(camera: object) -> None:
    if not isinstance(camera, dict) or set(camera) != {"center", "zoom", "bearing", "pitch"}:
        raise ValueError("Invalid camera.")
    center = camera["center"]
    if (
        not isinstance(center, list)
        or len(center) != 2
        or not all(_number(value) for value in center)
        or not -180 <= center[0] <= 180
        or not -90 <= center[1] <= 90
    ):
        raise ValueError("Camera centre must be longitude, latitude.")
    for key, low, high in (("zoom", 0, 22), ("bearing", -180, 180), ("pitch", 0, 85)):
        if not _number(camera[key]) or not low <= camera[key] <= high:
            raise ValueError(f"Camera {key} is out of range.")


def _filters(filters: object) -> None:
    if not isinstance(filters, dict):
        raise ValueError("Filters must be an object.")
    for key, value in filters.items():
        if key in FILTER_CHOICES:
            if type(value) not in (str, int) or value not in FILTER_CHOICES[key]:
                raise ValueError(f"Unknown value for filter {key}.")
        elif key in BOOLEAN_FILTERS:
            if type(value) is not bool:
                raise ValueError(f"Filter {key} must be true or false.")
        elif key in TEXT_FILTERS:
            if not isinstance(value, str) or len(value) > TEXT_FILTERS[key]:
                raise ValueError(f"Filter {key} is too long.")
        else:
            raise ValueError("Live views may only name known filters.")


def _number(value: object) -> TypeGuard[float]:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _uuid(value: object) -> None:
    if not isinstance(value, str):
        raise ValueError("Linked records are referenced by ID.")
    try:
        UUID(value)
    except ValueError:
        raise ValueError("Linked records are referenced by ID.") from None
