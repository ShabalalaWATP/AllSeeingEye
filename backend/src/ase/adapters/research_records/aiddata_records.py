"""Bounded GeoGCDF project GeoJSON parsing with attributed historical semantics."""

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, DecimalException
from typing import Any

from ase.domain.evidence_geometry import EvidenceGeometry, LocationRole
from ase.domain.project import ProjectMetadata

MAX_PROJECT_BYTES = 5 * 1024 * 1024
RELEASE_ID = "v3.0.1"
RELEASE_COMMIT = "0ed90518dddfef9a39acfe45716148b5700d478b"
SOURCE_ID = "research-aiddata-projects"
ATTRIBUTION = "AidData; OpenStreetMap contributors"
LIMITATIONS = (
    "Historical source-reported project facts, not current verified conditions. "
    "Commitments are not payments. Dates retain year precision. "
    "Source geometry may combine approximate/admin locations and OSM features; "
    "points/lines may be buffered and dissolved. It is not a measured site boundary "
    "or an accuracy radius."
)


@dataclass(frozen=True, slots=True)
class AidDataRecord:
    title: str
    recipient: str
    sector: str
    amount_constant_usd_2021: str | None
    project: ProjectMetadata
    geometry: EvidenceGeometry | None

    @property
    def source_url(self) -> str:
        return (
            "https://raw.githubusercontent.com/aiddata/gcdf-geospatial-data/"
            f"{RELEASE_COMMIT}/latest/geojsons/{self.project.project_id}.geojson"
        )


def _number(token: str) -> Decimal:
    if len(token) > 100:
        raise ValueError("Project numeric token exceeds its bound")
    value = Decimal(token)
    if not value.is_finite() or abs(value.adjusted()) > 1000:
        raise ValueError("Project numeric exponent exceeds its bound")
    return value


def _constant(token: str) -> None:
    raise ValueError("Non-finite JSON constants are unsupported")


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("Duplicate project JSON key")
        output[key] = value
    return output


def _text(value: Any, limit: int, *, unknown: str = "Unknown") -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        return unknown
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError("Invalid project text")
    value.encode("utf-8")
    return value


def _year(value: Any) -> int | None:
    if value is None:
        return None
    if type(value) not in (int, Decimal) or not Decimal(value).is_finite():
        raise ValueError("Invalid source project year")
    if not 1 <= value <= 9998 or value != int(value):
        raise ValueError("Invalid source project year")
    return int(value)


def _amount(value: Any) -> str | None:
    if value is None:
        return None
    if type(value) not in (int, Decimal) or not Decimal(value).is_finite():
        raise ValueError("Invalid source project amount")
    result = str(value)
    if len(result) > 100:
        raise ValueError("Project amount exceeds its bound")
    return result


def parse_project(data: bytes, *, expected_id: str) -> AidDataRecord:
    """Parse one native project; the file hash identifies bytes, not authenticity."""
    if not re.fullmatch(r"[0-9]{1,12}", expected_id) or not 0 < len(data) <= MAX_PROJECT_BYTES:
        raise ValueError("Invalid project identity or size")
    try:
        raw = json.loads(
            data, parse_float=_number, parse_constant=_constant, object_pairs_hook=_object
        )
        if not isinstance(raw, dict) or raw.get("type") != "FeatureCollection":
            raise ValueError("Expected native project FeatureCollection")
        if "crs" in raw:
            raise ValueError(
                "Explicit coordinate systems are unsupported; use native WGS84 GeoJSON"
            )
        features = raw.get("features")
        if not isinstance(features, list) or len(features) != 1:
            raise ValueError("Expected one combined project feature")
        feature = features[0]
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError("Expected native project feature")
        if "crs" in feature:
            raise ValueError("Explicit feature coordinate systems are unsupported")
        properties = feature.get("properties")
        if not isinstance(properties, dict) or type(properties.get("id")) is not int:
            raise ValueError("Missing native project identity")
        if str(properties["id"]) != expected_id:
            raise ValueError("Project filename and record identity differ")
        project = ProjectMetadata(
            dataset_id="aiddata-geogcdf",
            release_id=RELEASE_ID,
            project_id=expected_id,
            source_sha256=hashlib.sha256(data).hexdigest(),
            recipient_iso3=_text(properties.get("Recipient.ISO-3"), 3, unknown=""),
            reported_status=_text(properties.get("Status"), 300),
            precision=_text(properties.get("osm_precision_list"), 100),
            attribution=ATTRIBUTION,
            data_licence="ODC-By-1.0",
            geometry_licence="ODbL-1.0",
            limitations=LIMITATIONS,
            commitment_year=_year(properties.get("Commitment.Year")),
            implementation_year=_year(properties.get("Implementation.Start.Year")),
            completion_year=_year(properties.get("Completion.Year")),
        )
        geometry = None
        if feature.get("geometry") is not None:
            geometry = EvidenceGeometry(
                json.dumps(feature["geometry"], default=float, allow_nan=False),
                LocationRole.PROJECT_SITE,
                project.precision,
                "AidData OSM-derived project geometry; may include buffered/dissolved features",
                SOURCE_ID,
                ATTRIBUTION,
            )
        return AidDataRecord(
            _text(properties.get("Title"), 5000),
            _text(properties.get("Recipient"), 300),
            _text(properties.get("Sector.Name"), 300),
            _amount(properties.get("Amount.(Constant.USD.2021)")),
            project,
            geometry,
        )
    except (TypeError, ValueError, OverflowError, RecursionError, DecimalException) as exc:
        raise ValueError("Invalid or unsupported AidData project record") from exc
