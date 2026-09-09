"""NASA's published rolling 24-hour NOAA-20 CSV, available without a MAP_KEY."""

import csv
import io
from dataclasses import replace
from datetime import datetime, timedelta

from ase.adapters.feeds.firms import FIELDS, ORIGIN, SPEC, parse_firms_row
from ase.adapters.feeds.firms_parse_worker import parse_off_loop
from ase.adapters.feeds.firms_selection import FirmsSelection
from ase.adapters.feeds.firms_sensors import NOAA20, FirmsSensor, require_sensor
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.application.ports import Clock
from ase.domain.events import Event
from ase.domain.sources import SourceSpec

PUBLIC_URL = f"{ORIGIN}/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv"
MAX_PUBLIC_BYTES = 16 * 1024 * 1024
MAX_PUBLIC_ROWS = 150_000
PUBLIC_FIRMS = replace(
    SPEC,
    id="firms_public_noaa20",
    name="NASA FIRMS: public NOAA-20 24-hour detections",
    url=PUBLIC_URL,
    requires_key=False,
    poll_interval=timedelta(minutes=30),
)
_CONFIDENCE = {"low": "l", "nominal": "n", "high": "h"}


def public_sensor_spec(sensor: FirmsSensor = NOAA20) -> SourceSpec:
    sensor = require_sensor(sensor)
    return replace(
        PUBLIC_FIRMS,
        id=f"firms_public_{sensor.suffix}",
        name=f"NASA FIRMS: public {sensor.name} 24-hour detections",
        url=ORIGIN + sensor.public_path,
    )


def parse_public_firms(payload: bytes, now: datetime, sensor: FirmsSensor = NOAA20) -> list[Event]:
    """Validate the complete published batch, including fields not displayed on the map."""
    spec = public_sensor_spec(sensor)
    if len(payload) > MAX_PUBLIC_BYTES:
        raise FeedFetchError("Public FIRMS response exceeds the collection byte limit")
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), strict=True)
        header = reader.fieldnames
        required = FIELDS - {"instrument"}
        if header is None or len(header) != len(set(header)) or not set(header) >= required:
            raise ValueError
        selection = FirmsSelection()
        for index, row in enumerate(reader):
            if index >= MAX_PUBLIC_ROWS:
                raise FeedFetchError("Public FIRMS response exceeds the collection row limit")
            if None in row or any(row.get(name) is None for name in required):
                raise ValueError
            # This fixed published product is VIIRS. Its confidence codes differ
            # from the Area API; retain the same sensor semantics after normalisation.
            if "instrument" in row and row["instrument"] != "VIIRS":
                raise ValueError
            row["instrument"] = "VIIRS"
            row["confidence"] = _CONFIDENCE[row["confidence"]]
            event = parse_firms_row(row, now, spec, sensor)
            selection.add(event)
        return selection.finish()
    except (ValueError, KeyError, csv.Error, OverflowError):
        raise FeedFetchError("Public FIRMS returned an invalid observation batch") from None


class FirmsPublicConnector:
    spec = PUBLIC_FIRMS

    def __init__(self, http: FeedHttpClient, clock: Clock, *, sensor: FirmsSensor = NOAA20) -> None:
        self.http, self.clock = http, clock
        self.sensor = require_sensor(sensor)
        self.spec = public_sensor_spec(sensor)

    async def fetch(self) -> list[Event]:
        payload = await self.http.get_bytes(self.spec.url, max_redirects=0)
        return await parse_off_loop(parse_public_firms, payload, self.clock.now(), self.sensor)
