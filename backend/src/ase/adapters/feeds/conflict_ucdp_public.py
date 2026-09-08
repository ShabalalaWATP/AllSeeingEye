"""Token-free, fixed-version UCDP candidate CSV, bounded before and during parsing."""

from __future__ import annotations

import asyncio
import csv
import io
from dataclasses import replace

from ase.adapters.feeds.conflict_ucdp import UcdpRecords
from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.application.ports import Clock
from ase.domain.events import Event

MAX_ROWS = 10_000
REQUIRED_COLUMNS = frozenset({"id", "type_of_violence", "date_start", "date_end"})


class UcdpPublicCandidateConnector(UcdpRecords):
    def __init__(self, http: FeedHttpClient, clock: Clock, version: str) -> None:
        super().__init__(http, clock, version)
        self.spec = replace(
            self.spec,
            url="https://ucdp.uu.se/downloads/candidateged/GEDEvent_v"
            + version.replace(".", "_")
            + ".csv",
            requires_key=False,
            flags=frozenset({"monthly_release", "provisional", "public_csv"}),
        )

    async def fetch(self) -> list[Event]:
        try:
            # Daily refresh keeps the bounded event store populated without assigning
            # collection time as an incident date. Monthly inputs are immutable.
            raw = await self._http.get_text(self.spec.url, conditional=False)
        except NotModified:
            return []
        reader = csv.DictReader(io.StringIO(raw.lstrip("\ufeff")))
        if not REQUIRED_COLUMNS.issubset(reader.fieldnames or []):
            raise FeedFetchError("UCDP candidate CSV is missing required columns.")
        now = self._clock.now()
        events: dict[str, Event] = {}
        try:
            for index, row in enumerate(reader):
                if index >= MAX_ROWS:
                    raise FeedFetchError("UCDP candidate CSV exceeds monthly collection capacity.")
                if event := self._to_event(row, now):
                    events[event.id] = event
                if index % 250 == 249:
                    await asyncio.sleep(0)
        except csv.Error:
            raise FeedFetchError("UCDP candidate CSV contains an invalid field.") from None
        return list(events.values())
