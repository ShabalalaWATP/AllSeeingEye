"""Bounded original source geometry, independent of annotation display topology.

Structural validation establishes WGS84 coordinates, not geometric truth, valid
topology or usable sensor coverage. Rendering may reject unsupported topology
without discarding the retained coordinates.
"""

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

MAX_GEOMETRY_BYTES = 5 * 1024 * 1024
MAX_GEOMETRY_VERTICES = 100_000


class LocationRole(StrEnum):
    INCIDENT = "incident"
    REPORTED_AREA = "reported_area"
    REGISTERED_OFFICE = "registered_office"
    PROJECT_SITE = "project_site"
    PUBLISHER_LOCATION = "publisher_location"
    OBSERVATION_FOOTPRINT = "observation_footprint"
    ANALYST_ANNOTATION = "analyst_annotation"


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate source geometry keys")
        result[key] = value
    return result


def _read_geometry(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_GEOMETRY_BYTES:
        raise ValueError("Source geometry exceeds the 5 MiB limit")
    try:
        raw = json.loads(text, object_pairs_hook=_object)
    except (ValueError, RecursionError) as exc:
        raise ValueError("Invalid source geometry JSON") from exc
    if not isinstance(raw, dict) or set(raw) != {"type", "coordinates"}:
        raise ValueError("Source geometry requires only type and coordinates")
    return raw


def _canonical(text: str) -> tuple[str, int]:
    raw = _read_geometry(text)
    vertices = 0

    def point(value: Any) -> None:
        nonlocal vertices
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError("Expected a WGS84 longitude/latitude pair")
        if any(
            type(n) not in (int, float) or (isinstance(n, float) and not math.isfinite(n))
            for n in value
        ):
            raise ValueError("Source coordinates must be finite numbers")
        if not -180 <= value[0] <= 180 or not -90 <= value[1] <= 90:
            raise ValueError("Source coordinates are outside WGS84 bounds")
        vertices += 1
        if vertices > MAX_GEOMETRY_VERTICES:
            raise ValueError("Source geometry exceeds 100,000 vertices")

    def sequence(value: Any, minimum: int) -> list[Any]:
        if not isinstance(value, list) or not minimum <= len(value) <= MAX_GEOMETRY_VERTICES:
            raise ValueError("Invalid source geometry coordinate sequence")
        return value

    def line(value: Any, *, ring: bool = False) -> None:
        for coordinate in sequence(value, 4 if ring else 2):
            point(coordinate)
        if ring and value[0] != value[-1]:
            raise ValueError("Source polygon rings must be closed")

    def polygon(value: Any) -> None:
        for ring in sequence(value, 1):
            line(ring, ring=True)

    kind, coordinates = raw["type"], raw["coordinates"]
    if kind == "Point":
        point(coordinates)
    elif kind == "MultiPoint":
        for coordinate in sequence(coordinates, 1):
            point(coordinate)
    elif kind == "LineString":
        line(coordinates)
    elif kind == "MultiLineString":
        for segment in sequence(coordinates, 1):
            line(segment)
    elif kind == "Polygon":
        polygon(coordinates)
    elif kind == "MultiPolygon":
        for part in sequence(coordinates, 1):
            polygon(part)
    else:
        raise ValueError("Unsupported source geometry type")
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(canonical.encode("utf-8")) > MAX_GEOMETRY_BYTES:
        raise ValueError("Canonical source geometry exceeds the 5 MiB limit")
    return canonical, vertices


@dataclass(frozen=True, slots=True)
class EvidenceGeometry:
    source_geometry: str
    location_role: LocationRole
    precision: str
    method: str
    source_id: str
    attribution: str
    sha256: str = field(init=False)
    vertices: int = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.location_role, LocationRole):
            raise ValueError("Choose an explicit source location role")
        for value, limit in (
            (self.precision, 100),
            (self.method, 300),
            (self.source_id, 300),
            (self.attribution, 1000),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError("Source geometry metadata is missing or oversized")
            value.encode("utf-8")
        canonical, vertices = _canonical(self.source_geometry)
        object.__setattr__(self, "source_geometry", canonical)
        object.__setattr__(self, "vertices", vertices)
        object.__setattr__(self, "sha256", hashlib.sha256(canonical.encode("utf-8")).hexdigest())

    def to_geometry(self) -> dict[str, Any]:
        value: dict[str, Any] = json.loads(self.source_geometry)
        return value


def geometry_to_dict(value: EvidenceGeometry) -> dict[str, Any]:
    return {
        "geometry": value.to_geometry(),
        "sha256": value.sha256,
        "location_role": value.location_role.value,
        "precision": value.precision,
        "method": value.method,
        "source_id": value.source_id,
        "attribution": value.attribution,
    }


def geometry_from_dict(value: Any) -> EvidenceGeometry | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {
        "geometry",
        "sha256",
        "location_role",
        "precision",
        "method",
        "source_id",
        "attribution",
    }:
        raise ValueError("Invalid frozen source geometry")
    try:
        geometry = EvidenceGeometry(
            json.dumps(value["geometry"], allow_nan=False),
            LocationRole(value["location_role"]),
            value["precision"],
            value["method"],
            value["source_id"],
            value["attribution"],
        )
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError("Invalid frozen source geometry") from exc
    if geometry.sha256 != value["sha256"]:
        raise ValueError("Frozen source geometry hash mismatch")
    return geometry
