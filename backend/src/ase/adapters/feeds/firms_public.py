"""NASA's published rolling 24-hour NOAA-20 CSV, available without a MAP_KEY."""

import asyncio
import csv
import io
from dataclasses import replace
from datetime import datetime, timedelta

from ase.adapters.feeds.firms import FIELDS, ORIGIN, SPEC, parse_firms_row
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient
from ase.application.ports import Clock
from ase.domain.events import Event

PUBLIC_URL = f"{ORIGIN}/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv"
MAX_PUBLIC_BYTES = 10 * 1024 * 1024
MAX_PUBLIC_ROWS = 100_000
PUBLIC_FIRMS = replace(
    SPEC,
    id="firms_public_noaa20",
    name="NASA FIRMS: public NOAA-20 24-hour detections",
    url=PUBLIC_URL,
    requires_key=False,
    poll_interval=timedelta(minutes=30),
)
_CONFIDENCE = {"low": "l", "nominal": "n", "high": "h"}


def parse_public_firms(payload: bytes, now: datetime) -> list[Event]:
    """Validate the complete published batch, including fields not displayed on the map."""
    if len(payload) > MAX_PUBLIC_BYTES:
        raise FeedFetchError("Public FIRMS response exceeds the collection byte limit")
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")), strict=True)
        header = reader.fieldnames
        required = FIELDS - {"instrument"}
        if header is None or len(header) != len(set(header)) or not set(header) >= required:
            raise ValueError
        events: dict[str, Event] = {}
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
            event = parse_firms_row(row, now, PUBLIC_FIRMS)
            events[event.id] = event
        return list(events.values())
    except (ValueError, KeyError, csv.Error, OverflowError):
        raise FeedFetchError("Public FIRMS returned an invalid observation batch") from None


class FirmsPublicConnector:
    spec = PUBLIC_FIRMS

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self.http, self.clock = http, clock

    async def fetch(self) -> list[Event]:
        payload = await self.http.get_bytes(PUBLIC_URL, max_redirects=0)
        return await asyncio.to_thread(parse_public_firms, payload, self.clock.now())
