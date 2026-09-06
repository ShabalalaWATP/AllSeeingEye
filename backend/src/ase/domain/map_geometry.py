"""Strict bounded canonical GeoJSON for explicitly saved immutable map views.

Only geometry and a plain label survive normalisation. Input identifiers, URLs,
styles and arbitrary metadata are discarded; no resources are ever resolved.
Coordinates/winding remain original. Straight lines keep canonical seam crossings,
while their derived display-vertex count matches the frontend's seam splitter.
"""

import hashlib
import json
import math
from dataclasses import dataclass
from itertools import pairwise
from typing import Any, NoReturn

from ase.domain.map_topology import (
    MAX_POLYGON_VERTICES,
    Position,
    Ring,
    TopologyBudget,
    validate_polygon,
)

MAX_GEOJSON_BYTES = 5 * 1024 * 1024
MAX_GEOJSON_FEATURES = 2000
MAX_GEOJSON_VERTICES = 100_000
MAX_JSON_DEPTH = 16
MAX_LABEL_CHARACTERS = 300


@dataclass(frozen=True, slots=True)
class CanonicalMapGeometry:
    canonical_json: str
    sha256: str
    feature_count: int
    vertices: int
    display_vertices: int

    def to_collection(self) -> dict[str, Any]:
        """Return a fresh object so consumers cannot mutate the frozen canonical value."""
        value: dict[str, Any] = json.loads(self.canonical_json)
        return value


def _depth(text: str) -> None:
    depth = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise ValueError("GeoJSON exceeds the 16-level JSON depth limit.")
        elif char in "]}":
            depth -= 1
            if depth < 0:
                raise ValueError("Invalid GeoJSON JSON structure.")
    if depth or quoted:
        raise ValueError("Invalid GeoJSON JSON structure.")


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate GeoJSON object keys are unsupported.")
        if key == "crs":
            raise ValueError("Only WGS84 longitude/latitude is supported. Remove the declared CRS.")
        result[key] = value
    return result


def _finite_number(raw: str) -> float:
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError("Non-finite GeoJSON numbers are unsupported.")
    return value


def _constant(_: str) -> NoReturn:
    raise ValueError("Non-finite GeoJSON numbers are unsupported.")


def _unicode(value: object) -> None:
    if isinstance(value, str):
        value.encode("utf-8")
    elif isinstance(value, dict):
        for key, item in value.items():
            _unicode(key)
            _unicode(item)
    elif isinstance(value, list):
        for item in value:
            _unicode(item)


def _object(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Expected a GeoJSON object.")
    return value


def _array(value: object, minimum: int = 1) -> list[Any]:
    if not isinstance(value, list) or not minimum <= len(value) <= MAX_GEOJSON_VERTICES:
        raise ValueError("Invalid or oversized geometry coordinates.")
    return value


class _GeometryReader:
    def __init__(self, topology: TopologyBudget | None = None) -> None:
        self.vertices = 0
        self.extra_display_vertices = 0
        self.topology = topology if topology is not None else TopologyBudget()

    def point(self, raw: object) -> Position:
        values = _array(raw, 2)
        if (
            len(values) != 2
            or any(
                isinstance(value, bool)
                or not isinstance(value, int | float)
                or not math.isfinite(value)
                for value in values
            )
            or abs(values[0]) > 180
            or abs(values[1]) > 90
        ):
            raise ValueError("Coordinates must be finite WGS84 pairs. Altitude is unsupported.")
        self.vertices += 1
        if self.vertices > MAX_GEOJSON_VERTICES:
            raise ValueError("GeoJSON is limited to 100,000 vertices.")
        # JSON/JavaScript has one numeric type. Normalise integer spellings and -0
        # without rounding fractional coordinates or changing their precision.
        lon, lat = float(values[0]), float(values[1])
        return (int(lon) if lon.is_integer() else lon, int(lat) if lat.is_integer() else lat)

    def line(self, raw: object, *, split: bool = False) -> Ring:
        line = tuple(self.point(value) for value in _array(raw, 2))
        if split:
            for a, b in pairwise(line):
                if abs(b[0] - a[0]) > 180:
                    shifted = b[0] + (-360 if b[0] > a[0] else 360)
                    if shifted != a[0]:
                        self.extra_display_vertices += 2
        return line

    def polygon(self, raw: object) -> tuple[Ring, ...]:
        rings = []
        count = 0
        for ring in _array(raw):
            values = _array(ring, 4)
            count += len(values)
            if count > MAX_POLYGON_VERTICES:
                raise ValueError("Each polygon is limited to 256 vertices. Simplify the geometry.")
            rings.append(self.line(values))
        result = tuple(rings)
        validate_polygon(result, self.topology)
        return result

    def geometry(self, raw: object) -> dict[str, Any]:
        item = _object(raw)
        kind, values = item.get("type"), item.get("coordinates")
        match kind:
            case "Point":
                coordinates: object = self.point(values)
            case "MultiPoint":
                coordinates = tuple(self.point(value) for value in _array(values))
            case "LineString":
                coordinates = self.line(values, split=True)
            case "MultiLineString":
                coordinates = tuple(self.line(value, split=True) for value in _array(values))
            case "Polygon":
                coordinates = self.polygon(values)
            case "MultiPolygon":
                coordinates = tuple(self.polygon(value) for value in _array(values))
            case _:
                raise ValueError("Unsupported geometry. Use points, lines or polygons.")
        return {"type": kind, "coordinates": coordinates}


def parse_map_geometry(
    data: bytes | str, *, topology: TopologyBudget | None = None
) -> CanonicalMapGeometry:
    """Parse once after byte/depth checks; reject ambiguous JSON before canonicalising."""
    try:
        encoded = data.encode("utf-8") if isinstance(data, str) else data
        if len(encoded) > MAX_GEOJSON_BYTES:
            raise ValueError("GeoJSON is limited to 5 MiB.")
        text = encoded.decode("utf-8")
        _depth(text)
        raw = json.loads(
            text,
            object_pairs_hook=_json_object,
            parse_constant=_constant,
            parse_int=_finite_number,
            parse_float=_finite_number,
        )
        _unicode(raw)
    except UnicodeError as exc:
        raise ValueError("GeoJSON must contain valid UTF-8 Unicode text.") from exc
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Invalid GeoJSON JSON structure.") from exc
    root = _object(raw)
    if root.get("type") != "FeatureCollection":
        raise ValueError("Import a GeoJSON FeatureCollection.")
    features = _array(root.get("features"))
    if len(features) > MAX_GEOJSON_FEATURES:
        raise ValueError("GeoJSON is limited to 2,000 features.")
    reader = _GeometryReader(topology)
    normalised = []
    for index, raw_feature in enumerate(features):
        feature = _object(raw_feature)
        if feature.get("type") != "Feature":
            raise ValueError("Every collection entry must be a Feature.")
        properties = _object(feature["properties"]) if feature.get("properties") is not None else {}
        label = next(
            (
                properties[key]
                for key in ("name", "title", "label")
                if isinstance(properties.get(key), str)
            ),
            f"Feature {index + 1}",
        )
        normalised.append(
            {
                "type": "Feature",
                "id": index,
                "geometry": reader.geometry(feature.get("geometry")),
                "properties": {"label": label[:MAX_LABEL_CHARACTERS]},
            }
        )
    display_vertices = reader.vertices + reader.extra_display_vertices
    if display_vertices > MAX_GEOJSON_VERTICES:
        raise ValueError(
            "Antimeridian splitting exceeds 100,000 display vertices. Simplify the geometry."
        )
    canonical = json.dumps(
        {"type": "FeatureCollection", "features": normalised},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    encoded = canonical.encode("utf-8")
    if len(encoded) > MAX_GEOJSON_BYTES:
        raise ValueError("Canonical GeoJSON exceeds the 5 MiB limit.")
    return CanonicalMapGeometry(
        canonical,
        hashlib.sha256(encoded).hexdigest(),
        len(features),
        reader.vertices,
        display_vertices,
    )
