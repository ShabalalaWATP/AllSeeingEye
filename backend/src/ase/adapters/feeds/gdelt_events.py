"""GDELT 2.0 events: machine-coded protest and conflict events from the 15-minute export files.

The GEO and DOC APIs are rate limited or unavailable, so this connector follows
`lastupdate.txt` to the newest `export.CSV.zip`, keeps only the CAMEO root codes for
protest, force posture, coercion, assault, fighting and mass violence. These are
unreviewed media signals, not confirmed conflict incidents. Source counts do not
establish credibility or relevance; source-text screening is a separate stage.
"""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import UTC, datetime, timedelta

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
from ase.application.ports import Clock
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    GeoConfidence,
    Point,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.sources import SourceKind, SourceSpec

SPEC = SourceSpec(
    id="gdelt_events",
    name="GDELT 2.0 media signals (unreviewed)",
    organisation="The GDELT Project",
    category=Category.CONFLICT,
    kind=SourceKind.API,
    url="https://data.gdeltproject.org/gdeltv2/lastupdate.txt",
    reliability=Reliability.C,
    poll_interval=timedelta(minutes=15),
    licence_note="Free for any use with attribution to gdeltproject.org",
    homepage="https://www.gdeltproject.org/",
    flags=frozenset({"machine_coded"}),
)

MAX_CSV_BYTES = 20 * 1024 * 1024
MAX_EVENTS = 400
COLUMNS = 61
ROOT_CODES = {
    "14": ("protest", "Protest"),
    "15": ("force_posture", "Show of force"),
    "17": ("coercion", "Coercion"),
    "18": ("assault", "Assault"),
    "19": ("fight", "Fighting"),
    "20": ("mass_violence", "Mass violence"),
}
GEO_TYPES = {
    "1": GeoConfidence.COUNTRY,
    "2": GeoConfidence.ADMIN1,
    "3": GeoConfidence.CITY,
    "4": GeoConfidence.CITY,
    "5": GeoConfidence.ADMIN1,
}
_EXPORT_SUFFIX = ".export.CSV.zip"
_DATA_HOST = "https://data.gdeltproject.org/gdeltv2/"


def export_url(lastupdate: str) -> str:
    """The export file named on the first line of lastupdate.txt, forced onto https."""
    for line in lastupdate.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2].endswith(_EXPORT_SUFFIX):
            name = parts[2].rsplit("/", 1)[-1]
            if name.replace(_EXPORT_SUFFIX, "").isdigit():
                return _DATA_HOST + name
    raise FeedFetchError("GDELT lastupdate.txt names no export file")


def read_export(data: bytes) -> list[list[str]]:
    """The tab-separated rows inside the export zip, size-checked before inflation."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        members = archive.infolist()
        if len(members) != 1:
            raise FeedFetchError("GDELT export zip must hold exactly one file")
        if members[0].file_size > MAX_CSV_BYTES:
            raise FeedFetchError("GDELT export is larger than allowed")
        # The declared size is untrusted metadata: count the inflated bytes as well.
        with archive.open(members[0]) as member:
            raw = member.read(MAX_CSV_BYTES + 1)
        if len(raw) > MAX_CSV_BYTES:
            raise FeedFetchError("GDELT export inflates beyond the allowed size")
        text = raw.decode("utf-8", "replace")
    except zipfile.BadZipFile as exc:
        raise FeedFetchError("GDELT export is not a zip file") from exc
    reader = csv.reader(io.StringIO(text), delimiter="\t", quoting=csv.QUOTE_NONE)
    return [row for row in reader if len(row) >= COLUMNS]


def _number(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _added(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
    except ValueError:
        return None


def _actor(name: str) -> str:
    return name.title() if name else ""


class GdeltEventsConnector:
    spec = SPEC

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock
        self._last_export: str | None = None

    async def fetch(self) -> list[Event]:
        try:
            listing = await self._http.get_text(self.spec.url, conditional=False)
        except NotModified:
            return []
        url = export_url(listing)
        if url == self._last_export:
            return []
        rows = read_export(await self._http.get_bytes(url, conditional=False))
        self._last_export = url
        now = self._clock.now()
        candidates = [row for row in rows if row[28] in ROOT_CODES and row[56] and row[57]]
        candidates.sort(key=lambda row: -(_number(row[31]) or 0))
        events: list[Event] = []
        seen: set[str] = set()
        for row in candidates:
            event = self._to_event(row, now)
            if event is None or event.id in seen:
                continue
            seen.add(event.id)
            events.append(event)
            if len(events) >= MAX_EVENTS:
                break
        return events

    def _to_event(self, row: list[str], now: datetime) -> Event | None:
        lat, lon = _number(row[56]), _number(row[57])
        if lat is None or lon is None or not row[0]:
            return None
        try:
            point = Point(lon=lon, lat=lat)
        except ValueError:
            return None
        subtype, label = ROOT_CODES[row[28]]
        actors = [name for name in (_actor(row[6]), _actor(row[16])) if name]
        goldstein = _number(row[30])
        mentions = int(_number(row[31]) or 0)
        sources = int(_number(row[32]) or 0)
        tone = _number(row[34])
        location = row[52] or "unknown location"
        title = f"{label}: {' and '.join(actors) if actors else 'unnamed actors'}, {location}"
        summary = (
            f"GDELT coded CAMEO event {row[26]} at {location}. "
            f"Goldstein {goldstein if goldstein is not None else 'n/a'}, "
            f"{mentions} mentions across {sources} sources, "
            f"average tone {tone:.1f}."
            if tone is not None
            else ""
        )
        url = row[60] if row[60].startswith(("https://", "http://")) else None
        return Event(
            id=event_id(self.spec.id, row[0]),
            source_id=self.spec.id,
            category=Category.CONFLICT,
            subtype=subtype,
            title=title,
            summary=summary or None,
            url=url,
            published_at=_added(row[59]) or now,
            observed_at=now,
            point=point,
            geo_confidence=GEO_TYPES.get(row[51], GeoConfidence.COUNTRY),
            tags=frozenset({subtype, "gdelt", "machine_coded", f"cameo_{row[26]}"}),
            severity=min(1.0, max(0.0, -(goldstein or 0.0) / 10.0)),
            reliability=self.spec.reliability,
            credibility=Credibility.CANNOT_BE_JUDGED,
            grade_rationale=(
                f"Machine-coded by GDELT from {sources} source(s); "
                "source counts do not establish independent corroboration; "
                "the point is the coded action geography, not a verified location"
            ),
            attributes=freeze_attributes(
                {
                    "event_code": row[26],
                    "root_code": row[28],
                    "quad_class": row[29],
                    "goldstein": goldstein,
                    "mentions": mentions,
                    "sources": sources,
                    "articles": int(_number(row[33]) or 0),
                    "tone": round(tone, 2) if tone is not None else None,
                    "actor1": _actor(row[6]) or None,
                    "actor2": _actor(row[16]) or None,
                    "location": row[52] or None,
                    "location_fips": row[53] or None,
                    "event_day": row[1] or None,
                    "batch": row[59] or None,
                }
            ),
            content_hash=content_hash(row[0], row[59]),
        )
