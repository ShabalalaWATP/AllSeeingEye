"""Country-attributed IODA event windows and Cloudflare Radar outage annotations.

Neither provider's country scope is an incident coordinate or proof of cause.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from ase.adapters.feeds.cyber import IODA, _measurement_time, _when
from ase.adapters.feeds.http import FeedCredential, FeedFetchError, FeedHttpClient, NotModified
from ase.application.ports import Clock
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    GeoConfidence,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.sources import SourceKind, SourceSpec

IODA_EVENTS = SourceSpec(
    id="ioda_outage_events",
    name="Internet outage event windows (IODA)",
    organisation=IODA.organisation,
    category=Category.CYBER,
    kind=SourceKind.API,
    url="https://api.ioda.inetintel.cc.gatech.edu/v2/outages/events",
    reliability=Reliability.B,
    poll_interval=timedelta(minutes=30),
    licence_note="Academic project; attribute IODA",
    homepage=IODA.homepage,
    instrument=True,
)
CLOUDFLARE_RADAR = SourceSpec(
    id="cloudflare_radar_outages",
    name="Internet outages (Cloudflare Radar)",
    organisation="Cloudflare Radar",
    category=Category.CYBER,
    kind=SourceKind.API,
    url="https://api.cloudflare.com/client/v4/radar/annotations/outages",
    reliability=Reliability.B,
    poll_interval=timedelta(minutes=30),
    licence_note="CC BY-NC 4.0; non-commercial use only, attribute Cloudflare Radar",
    homepage="https://radar.cloudflare.com/outage-center",
    requires_key=True,
    instrument=True,
)

_ISO = re.compile(r"[A-Z]{2}")
_MAX_ITEMS = 200


def _safe_label(value: object, *, limit: int = 120) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:limit]


class IodaEventsConnector:
    spec = IODA_EVENTS

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        now = self._clock.now()
        since = now - timedelta(days=1)
        query = urlencode(
            {
                "from": int(since.timestamp()),
                "until": int(now.timestamp()),
                "entityType": "country",
                "limit": _MAX_ITEMS,
            }
        )
        try:
            data = await self._http.get_json(f"{self.spec.url}?{query}", conditional=False)
        except NotModified:
            return []
        if (
            not isinstance(data, dict)
            or data.get("error")
            or not isinstance(data.get("data"), list)
        ):
            raise FeedFetchError("IODA response does not contain a valid event list")
        return [
            event
            for item in data["data"][:_MAX_ITEMS]
            if isinstance(item, dict) and (event := self._to_event(item, now, since))
        ]

    def _to_event(self, item: dict[str, Any], now: datetime, since: datetime) -> Event | None:
        location = item.get("location")
        if not isinstance(location, str) or not location.startswith("country/"):
            return None
        iso = location.removeprefix("country/")
        if not _ISO.fullmatch(iso):
            return None
        start = _measurement_time(item.get("start"))
        if start is None or start > now + timedelta(minutes=5):
            return None
        duration = item.get("duration")
        if not isinstance(duration, int | float) or isinstance(duration, bool):
            duration = None
        if duration is not None and (
            not math.isfinite(duration) or not 0 <= duration <= 60 * 60 * 24 * 90
        ):
            duration = None
        end = start + timedelta(seconds=duration) if duration is not None else None
        if end is not None and end < since:
            return None
        datasource = _safe_label(item.get("datasource"), limit=32) or "network measurement"
        method = _safe_label(item.get("method"), limit=32)
        country_name = _safe_label(item.get("location_name")) or iso
        key = f"{iso}:{int(start.timestamp())}:{datasource}:{method}"
        return Event(
            id=event_id(self.spec.id, key),
            source_id=self.spec.id,
            category=Category.CYBER,
            subtype="outage",
            title=f"IODA outage event signal: {country_name} ({datasource})",
            summary=(
                "IODA recorded a country-level network measurement anomaly window. "
                "Its country scope does not identify an exact outage site, cause or affected users."
            ),
            url=f"https://ioda.inetintel.cc.gatech.edu/country/{iso}",
            published_at=start,
            observed_at=now,
            geo_confidence=GeoConfidence.COUNTRY,
            country_iso=iso,
            tags=frozenset({"outage", "ioda_event", datasource}),
            severity=0.5,
            reliability=self.spec.reliability,
            credibility=Credibility.POSSIBLY_TRUE,
            grade_rationale=(
                "Automated IODA anomaly window; cause and impact not independently verified"
            ),
            attributes=freeze_attributes(
                {
                    "entity_type": "country",
                    "entity_code": iso,
                    "datasource": datasource,
                    "method": method or None,
                    "start": start.isoformat(),
                    "end": end.isoformat() if end else None,
                    "date_basis": (
                        "IODA event-window start; collection does not establish current status"
                    ),
                    "geography_basis": "IODA country aggregation; no precise incident location",
                    "attribution_status": "Connectivity anomaly, not evidence of a cyberattack",
                }
            ),
            content_hash=content_hash(key, country_name, str(duration), str(item.get("status"))),
        )


class CloudflareRadarConnector:
    spec = CLOUDFLARE_RADAR

    def __init__(self, http: FeedHttpClient, clock: Clock, token: str) -> None:
        self._http = http
        self._clock = clock
        self._credential = FeedCredential(
            origin="https://api.cloudflare.com", authorization=f"Bearer {token}"
        )

    async def fetch(self) -> list[Event]:
        query = urlencode({"dateRange": "7d", "limit": 100, "offset": 0, "format": "json"})
        try:
            data = await self._http.get_json(
                f"{self.spec.url}?{query}", credential=self._credential, conditional=False
            )
        except NotModified:
            return []
        if not isinstance(data, dict) or data.get("success") is not True:
            raise FeedFetchError("Cloudflare Radar returned an unsuccessful outage response")
        result = data.get("result")
        if not isinstance(result, dict) or not isinstance(result.get("annotations"), list):
            raise FeedFetchError("Cloudflare Radar response does not contain outage annotations")
        now = self._clock.now()
        events: list[Event] = []
        for item in result["annotations"][:100]:
            if not isinstance(item, dict):
                continue
            locations = item.get("locations")
            if not isinstance(locations, list):
                continue
            countries = tuple(
                dict.fromkeys(
                    value
                    for value in locations[:50]
                    if isinstance(value, str) and _ISO.fullmatch(value)
                )
            )
            for iso in countries or (None,):
                event = self._to_event(item, iso, now)
                if event:
                    events.append(event)
                if len(events) >= _MAX_ITEMS:
                    return events
        return events

    def _to_event(self, item: dict[str, Any], iso: str | None, now: datetime) -> Event | None:
        start = _when(item.get("startDate"))
        if start is None or start > now + timedelta(minutes=5):
            return None
        end = _when(item.get("endDate"))
        scope = _safe_label(item.get("scope"))
        event_type = _safe_label(item.get("eventType"), limit=32) or "OUTAGE"
        outage_data = item.get("outage")
        outage: dict[str, Any] = outage_data if isinstance(outage_data, dict) else {}
        outage_type = _safe_label(outage.get("outageType"), limit=48)
        cause = _safe_label(outage.get("outageCause"), limit=48)
        asns = item.get("asns")
        asn = str(asns[0]) if isinstance(asns, list) and asns and isinstance(asns[0], int) else ""
        identity = iso or (f"AS{asn}" if asn else "unlocated")
        details = item.get("locationsDetails")
        country_name = identity
        if iso and isinstance(details, list):
            country_name = (
                next(
                    (
                        _safe_label(detail.get("name"))
                        for detail in details[:50]
                        if isinstance(detail, dict) and detail.get("code") == iso
                    ),
                    "",
                )
                or iso
            )
        key = f"{identity}:{start.isoformat()}:{event_type}:{scope}:{outage_type}"
        return Event(
            id=event_id(self.spec.id, key),
            source_id=self.spec.id,
            category=Category.CYBER,
            subtype="outage",
            title=(
                f"Cloudflare Radar {event_type.lower().replace('_', ' ')}: {country_name}"
                + (f" ({outage_type.lower().replace('_', ' ')})" if outage_type else "")
            ),
            summary=(
                f"Cloudflare Radar reported {scope or 'an internet disruption'} for {identity}. "
                "The reported scope does not identify a precise site or verify the cause."
            ),
            url=self.spec.homepage,
            published_at=start,
            observed_at=now,
            geo_confidence=GeoConfidence.COUNTRY if iso else GeoConfidence.NONE,
            country_iso=iso,
            tags=frozenset({"outage", "cloudflare_radar", event_type.lower()}),
            severity=0.6,
            reliability=self.spec.reliability,
            credibility=Credibility.POSSIBLY_TRUE,
            grade_rationale="Cloudflare Radar annotation; scope and cause are provider assessments",
            attributes=freeze_attributes(
                {
                    "entity_type": "country" if iso else "asn" if asn else "unknown",
                    "entity_code": iso or asn or None,
                    "datasource": "Cloudflare Radar",
                    "event_type": event_type,
                    "scope": scope or None,
                    "outage_type": outage_type or None,
                    "reported_cause": cause or None,
                    "start": start.isoformat(),
                    "end": end.isoformat() if end else None,
                    "date_basis": (
                        "Cloudflare Radar annotated start; end absent does not prove ongoing"
                    ),
                    "geography_basis": (
                        "Cloudflare Radar reported country scope; no incident coordinates"
                    ),
                    "attribution_status": "Internet disruption, not evidence of a cyberattack",
                }
            ),
            content_hash=content_hash(key, country_name, str(item.get("endDate")), cause),
        )
