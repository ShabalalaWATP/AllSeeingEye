"""Bounded NOAA-20 VIIRS thermal observations from NASA FIRMS, never inferred attacks."""

import csv
import io
import math
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from ase.adapters.feeds.firms_parse_worker import parse_off_loop
from ase.adapters.feeds.firms_selection import FirmsSelection
from ase.adapters.feeds.firms_sensors import NOAA20, FirmsSensor, require_sensor
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.adapters.feeds.secret_urls import SecretFeedUrl
from ase.application.ports import Clock
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
from ase.domain.observation import ObservationMetadata
from ase.domain.sources import SourceKind, SourceSpec

ORIGIN = "https://firms.modaps.eosdis.nasa.gov"
PRODUCT = "VIIRS_NOAA20_NRT"
MAX_BYTES = 16 * 1024 * 1024
# The byte bound governs. The shortest observed world row is 73 bytes before its newline,
# and a real NOAA-21 two-date world response held 150,980 rows (15 September 2026).
MIN_ROW_BYTES = 72
MAX_ROWS = MAX_BYTES // MIN_ROW_BYTES
LIMITATIONS = (
    "Satellite thermal anomaly at a nominal 375 m pixel centre, not an exact fire boundary. "
    "Cloud, overpass timing and detection limits affect coverage. Heat does not establish "
    "cause, an attack or damage. Sensor confidence is not intelligence confidence."
)
SPEC = SourceSpec(
    id="firms_viirs_noaa20",
    name="NASA FIRMS: NOAA-20 thermal detections",
    organisation="NASA FIRMS",
    parent_organisation="NASA",
    category=Category.DISASTER,
    kind=SourceKind.API,
    url=f"{ORIGIN}/api/area/",
    reliability=Reliability.F,
    poll_interval=timedelta(minutes=15),
    requires_key=True,
    instrument=True,
    homepage=f"{ORIGIN}/",
    licence_note="NASA FIRMS data; acknowledge NASA LANCE/FIRMS.",
    flags=frozenset({"satellite_observation", "thermal_anomaly"}),
)
FIELDS = {
    "latitude",
    "longitude",
    "bright_ti4",
    "scan",
    "track",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
    "confidence",
    "version",
    "bright_ti5",
    "frp",
    "daynight",
}


def validate_area(value: str) -> str:
    if value == "world":
        return value
    try:
        parts = value.split(",")
        if len(parts) != 4:
            raise ValueError
        west, south, east, north = (float(part) for part in parts)
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise ValueError
        return ",".join(f"{number:g}" for number in (west, south, east, north))
    except ValueError:
        raise ValueError(
            "FIRMS area must be world or west,south,east,north without wrapping"
        ) from None


def _number(value: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError
    return result


def sensor_spec(sensor: FirmsSensor = NOAA20) -> SourceSpec:
    sensor = require_sensor(sensor)
    return replace(
        SPEC,
        id=f"firms_viirs_{sensor.suffix}",
        name=f"NASA FIRMS: {sensor.name} thermal detections",
    )


def parse_firms_row(
    row: dict[str, str], now: datetime, spec: SourceSpec = SPEC, sensor: FirmsSensor = NOAA20
) -> Event:
    sensor = require_sensor(sensor)
    point = Point(lon=float(row["longitude"]), lat=float(row["latitude"]))
    if not re.fullmatch(r"\d{1,4}", row["acq_time"], flags=re.ASCII):
        raise ValueError
    timestamp = datetime.strptime(
        row["acq_date"] + " " + row["acq_time"].zfill(4), "%Y-%m-%d %H%M"
    ).replace(tzinfo=UTC)
    if not now - timedelta(days=2) <= timestamp <= now + timedelta(minutes=5):
        raise ValueError
    if (
        row["satellite"] not in sensor.satellite_codes
        or row["instrument"] != "VIIRS"
        or row["confidence"] not in {"l", "n", "h"}
        or row["daynight"] not in {"D", "N"}
        or not re.fullmatch(r"\d+(?:\.\d+)?(?:NRT|URT|RT)?", row["version"])
    ):
        raise ValueError
    reported_frp = float(row["frp"])
    if not math.isfinite(reported_frp):
        raise ValueError
    limitations = LIMITATIONS
    if reported_frp < 0:
        limitations += (
            " Provider reports negative radiative power; this measurement is unavailable "
            "for interpretation."
        )
    attributes: dict[str, JsonScalar] = {
        "satellite": sensor.name,
        "instrument": "VIIRS",
        "product": sensor.product,
        "sensor_confidence": row["confidence"],
        "processing_version": row["version"],
        "daynight": row["daynight"],
        "nominal_pixel_metres": 375,
        "brightness_i4_kelvin": _number(row["bright_ti4"]),
        "brightness_i5_kelvin": _number(row["bright_ti5"]),
        "scan_km": _number(row["scan"]),
        "track_km": _number(row["track"]),
        "fire_radiative_power_mw": reported_frp if reported_frp >= 0 else None,
    }
    if reported_frp < 0:
        attributes["reported_fire_radiative_power_mw"] = reported_frp
        attributes["measurement_quality"] = "Negative provider FRP; power unavailable"
    identity = f"{timestamp.isoformat()}:{point.lon!r}:{point.lat!r}"
    identifier = event_id(spec.id, identity)
    return Event(
        id=identifier,
        source_id=spec.id,
        category=Category.DISASTER,
        subtype="thermal_detection",
        title=f"{sensor.name} VIIRS thermal detection",
        summary=limitations,
        url=f"{ORIGIN}/map/",
        published_at=timestamp,
        observed_at=now,
        point=point,
        geo_confidence=GeoConfidence.EXACT,
        reliability=Reliability.F,
        grade_rationale="Source reliability remains unassessed; sensor confidence is separate.",
        tags=frozenset({"firms", "viirs", "thermal_anomaly"}),
        attributes=freeze_attributes(attributes),
        content_hash=content_hash(*(row[name] for name in sorted(FIELDS))),
        observation=ObservationMetadata(timestamp, sensor.product, identifier, limitations),
    )


def parse_firms(payload: bytes, now: datetime, sensor: FirmsSensor = NOAA20) -> list[Event]:
    """Reject malformed/oversized batches atomically, rather than imply complete coverage."""
    spec = sensor_spec(sensor)
    if len(payload) > MAX_BYTES:
        raise FeedFetchError("FIRMS response exceeds the collection byte limit")
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), strict=True)
        header = reader.fieldnames
        if header is None or len(header) != len(set(header)) or not set(header) >= FIELDS:
            raise ValueError
        selection = FirmsSelection()
        for index, row in enumerate(reader):
            if index >= MAX_ROWS:
                raise FeedFetchError("FIRMS response exceeds the collection row limit")
            if None in row or any(row.get(name) is None for name in FIELDS):
                raise ValueError
            event = parse_firms_row(row, now, spec, sensor)
            selection.add(event)
        return selection.finish()
    except (ValueError, csv.Error, OverflowError):
        raise FeedFetchError("FIRMS returned an invalid observation batch") from None


class FirmsConnector:
    spec = SPEC

    def __init__(
        self,
        http: FeedHttpClient,
        clock: Clock,
        key: str,
        area: str = "world",
        *,
        sensor: FirmsSensor = NOAA20,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", key):
            raise ValueError("Invalid FIRMS map key format")
        self._http, self._clock = http, clock
        self.sensor = require_sensor(sensor)
        self.spec = sensor_spec(sensor)
        # NASA day ranges use UTC calendar dates. Include yesterday so a restart
        # just after midnight still collects detections before today's first delivery.
        self._target = SecretFeedUrl(
            ORIGIN, f"{ORIGIN}/api/area/csv/{key}/{sensor.product}/{validate_area(area)}/2"
        )

    async def fetch(self) -> list[Event]:
        payload = await self._http.get_secret_bytes(self._target)
        return await parse_off_loop(parse_firms, payload, self._clock.now(), self.sensor)
