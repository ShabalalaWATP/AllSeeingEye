"""Validate dated stationary air-quality observations and their reuse permissions."""

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from math import ceil, floor
from typing import Any

from shapely.geometry import Point as ShapePoint
from shapely.geometry import shape
from shapely.prepared import prep

from ase.adapters.research.feed import web_url
from ase.adapters.research.hazard_area import instant, number
from ase.domain.events import (
    Category,
    Event,
    GeoConfidence,
    JsonScalar,
    Point,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.evidence_geometry import EvidenceGeometry, LocationRole
from ase.domain.observation import ObservationMetadata
from ase.domain.research import ResearchQuery
from ase.domain.research_area import ResearchArea

SOURCE_ID = "research-openaq-area"
POLLUTANTS = frozenset({"pm25", "pm10", "pm1", "no2", "no", "nox", "so2", "o3", "co", "bc"})


def text(value: Any, maximum: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError("Missing or oversized OpenAQ metadata")
    if any(ord(char) < 32 for char in value):
        raise ValueError("Invalid OpenAQ metadata")
    value.encode("utf-8")
    return value


def identifier(value: Any) -> int:
    if type(value) is not int or not 0 < value < 2**63:
        raise ValueError("Invalid OpenAQ identifier")
    return value


def rows(payload: Any, maximum: int) -> list[Any]:
    values = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(values, list) or len(values) > maximum:
        raise ValueError("Invalid or oversized OpenAQ page")
    return values


def coordinates(raw: Any) -> Point:
    if not isinstance(raw, dict):
        raise ValueError("Missing observation coordinates")
    lon, lat = number(raw.get("longitude")), number(raw.get("latitude"))
    if lon is None or lat is None:
        raise ValueError("Invalid observation coordinates")
    return Point(lon, lat)


class OpenAqArea:
    def __init__(self, area: ResearchArea) -> None:
        polygon = shape(area.geometry.to_collection()["features"][0]["geometry"])
        if polygon.is_empty or not polygon.is_valid:
            raise ValueError("Unsupported area topology")
        west, south, east, north = polygon.bounds
        # OpenAQ truncates bbox inputs to four decimals; round outwards first.
        self.bbox = ",".join(
            f"{rounded / 10000:.4f}"
            for rounded in (
                floor(west * 10000),
                floor(south * 10000),
                ceil(east * 10000),
                ceil(north * 10000),
            )
        )
        self._polygon = prep(polygon)

    def contains(self, point: Point) -> bool:
        return bool(self._polygon.intersects(ShapePoint(point.lon, point.lat)))


def station(raw: Any, area: OpenAqArea) -> dict[str, Any] | None:
    if not isinstance(raw, dict) or raw.get("isMobile") is not False:
        return None
    identifier(raw.get("id"))
    text(raw.get("name"))
    if not area.contains(coordinates(raw.get("coordinates"))):
        return None
    sensors, licences = raw.get("sensors"), raw.get("licenses")
    if not isinstance(sensors, list) or not 1 <= len(sensors) <= 50:
        return None
    if not isinstance(licences, list) or not 1 <= len(licences) <= 4:
        return None
    return raw


def station_date(raw: dict[str, Any]) -> datetime:
    value = raw.get("datetimeLast")
    return (instant(value.get("utc")) if isinstance(value, dict) else None) or datetime.min.replace(
        tzinfo=UTC
    )


def applicable_licences(station: dict[str, Any], acquired: datetime) -> list[dict[str, Any]]:
    result = []
    for row in station["licenses"]:
        if not isinstance(row, dict):
            raise ValueError("Invalid station licence")
        identifier(row.get("id"))
        start = date.fromisoformat(text(row.get("dateFrom"), 10))
        end = date.fromisoformat(text(row["dateTo"], 10)) if row.get("dateTo") else None
        if end is not None and end < start:
            raise ValueError("Invalid licence interval")
        if start <= acquired.date() and (end is None or acquired.date() <= end):
            result.append(row)
    if not result:
        raise ValueError("No licence covers this measurement date")
    return result


@dataclass(frozen=True, slots=True)
class ReuseLicence:
    id: int
    name: str
    url: str
    attribution_required: bool

    @classmethod
    def parse(cls, payload: Any, expected_id: int) -> "ReuseLicence | None":
        data = rows(payload, 1)
        if len(data) != 1 or not isinstance(data[0], dict):
            raise ValueError("Missing OpenAQ licence")
        row = data[0]
        if identifier(row.get("id")) != expected_id:
            raise ValueError("Mismatched OpenAQ licence")
        # Reports can be shared and summarised. Do not impose hidden NC/ND/SA terms.
        if (
            any(
                row.get(key) is not True
                for key in ("commercialUseAllowed", "modificationAllowed", "redistributionAllowed")
            )
            or row.get("shareAlikeRequired") is not False
            or type(row.get("attributionRequired")) is not bool
        ):
            return None
        url = web_url(text(row.get("sourceUrl"), 300))
        if not url:
            return None
        return cls(expected_id, text(row.get("name"), 120), url, row["attributionRequired"])


def measurement(
    raw: Any, station: dict[str, Any], query: ResearchQuery, area: OpenAqArea, now: datetime
) -> tuple[datetime, Point, dict[str, Any], float]:
    if not isinstance(raw, dict) or identifier(raw.get("locationsId")) != station["id"]:
        raise ValueError("Measurement station mismatch")
    sensor_id = identifier(raw.get("sensorsId"))
    matches = [
        sensor
        for sensor in station["sensors"]
        if isinstance(sensor, dict) and sensor.get("id") == sensor_id
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("parameter"), dict):
        raise ValueError("Unknown or ambiguous sensor")
    identifier(matches[0].get("id"))
    parameter = matches[0]["parameter"]
    identifier(parameter.get("id"))
    if parameter.get("name") not in POLLUTANTS:
        raise ValueError("Not a supported pollutant")
    text(parameter.get("units"), 40)
    timestamp = raw.get("datetime")
    acquired = instant(timestamp.get("utc")) if isinstance(timestamp, dict) else None
    value, point = number(raw.get("value")), coordinates(raw.get("coordinates"))
    if (
        acquired is None
        or not query.since <= acquired < query.until
        or acquired > now
        or value is None
        or value < 0
        or not area.contains(point)
    ):
        raise ValueError("Measurement is outside the date/area/validation bounds")
    return acquired, point, parameter, value


def to_event(
    raw: dict[str, Any],
    station: dict[str, Any],
    acquired: datetime,
    point: Point,
    parameter: dict[str, Any],
    value: float,
    licences: list[tuple[dict[str, Any], ReuseLicence]],
    now: datetime,
) -> Event:
    provider, owner = station.get("provider"), station.get("owner")
    if not isinstance(provider, dict) or not isinstance(owner, dict):
        raise ValueError("Missing measurement provenance")
    provider_name, owner_name = text(provider.get("name"), 120), text(owner.get("name"), 120)
    station_name, sensor_id = text(station["name"]), identifier(raw["sensorsId"])
    attribution = f"{provider_name}; {owner_name}, via OpenAQ"
    identity = f"{sensor_id}:{acquired.isoformat()}"
    attributes: dict[str, JsonScalar] = {
        "collection_capability": SOURCE_ID,
        "station_id": station["id"],
        "station": station_name,
        "sensor_id": sensor_id,
        "parameter_id": parameter["id"],
        "pollutant": parameter["name"],
        "value": value,
        "units": parameter["units"],
        "provider": provider_name,
        "owner": owner_name,
        "provider_id": identifier(provider.get("id")),
        "owner_id": identifier(owner.get("id")),
    }
    licence_lines = []
    for index, (scope, licence) in enumerate(licences, 1):
        credit = scope.get("attribution")
        credit = credit if isinstance(credit, dict) else {}
        credit_name = text(credit.get("name"), 120) if credit.get("name") else ""
        credit_url = web_url(text(credit["url"], 300)) if credit.get("url") else None
        if (licence.attribution_required and not credit_name) or (
            credit.get("url") and not credit_url
        ):
            raise ValueError("Licence attribution is missing or invalid")
        interval = f"{scope['dateFrom']} to {scope.get('dateTo') or 'open-ended'}"
        prefix = f"licence_{index}"
        attributes.update(
            {
                prefix: f"{licence.id}: {licence.name}",
                f"{prefix}_url": licence.url,
                f"{prefix}_attribution": credit_name,
                f"{prefix}_attribution_url": credit_url,
                f"{prefix}_dates": interval,
                f"{prefix}_permissions": "commercial/modification/redistribution allowed; "
                f"share-alike not required; attribution required: {licence.attribution_required}",
            }
        )
        licence_lines.append(
            f"{licence.name} ({licence.url}), attribution: {credit_name or attribution}"
            + (f" ({credit_url})" if credit_url else "")
            + f", applicable {interval}."
        )
    summary = (
        "Dated station value only, not a historical series, AQI, health assessment or "
        "area-wide pollution estimate. "
        f"{parameter['name']}: {value:g} {parameter['units']} at {station_name}, "
        f"measured {acquired.isoformat()}. Provider: {provider_name}. Owner: {owner_name}. "
        "Retrieved through OpenAQ. Latest available sensor value, not a historical series, "
        "AQI, health assessment or evidence of conditions across the area. "
        + " ".join(licence_lines)
    )
    if len(summary) > 2000:
        raise ValueError("Required licence/provenance text exceeds evidence bounds")
    geometry = EvidenceGeometry(
        json.dumps({"type": "Point", "coordinates": [point.lon, point.lat]}),
        LocationRole.OBSERVATION_FOOTPRINT,
        "source-reported sensor point",
        "Exact local polygon intersection of the reported measurement coordinates; "
        "no inferred pollution extent",
        SOURCE_ID,
        attribution,
    )
    return Event(
        id=event_id(SOURCE_ID, identity),
        source_id=SOURCE_ID,
        category=Category.HUMANITARIAN,
        subtype="air_quality_measurement",
        title=f"{parameter['name']}: {value:g} {parameter['units']} at {station_name}"[:300],
        summary=summary,
        url=f"https://explore.openaq.org/locations/{station['id']}",
        published_at=None,
        observed_at=now,
        reliability=Reliability.F,
        point=point,
        geo_confidence=GeoConfidence.EXACT,
        tags=frozenset({"air_quality", "environment", parameter["name"]}),
        attributes=freeze_attributes(attributes),
        geometry=geometry,
        observation=ObservationMetadata(
            acquired_at=acquired,
            collection_id="openaq-v3-latest",
            item_id=identity,
            limitations="Measurement timestamp, not retrieval or station last-active time. "
            "Reported instrument quality and averaging interval are not independently verified. "
            "Latest endpoint can contain old readings; no spatial interpolation or health claim.",
        ),
        content_hash=content_hash(summary, geometry.sha256, acquired.isoformat()),
    )
