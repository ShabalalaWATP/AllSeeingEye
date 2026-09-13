"""Cyber feeds: ransomware victim claims (ransomware.live) and internet outage alerts (IODA).

Country references describe source-reported scope, without incident coordinates.
Outage measurements do not establish a cyberattack or a responsible actor.
"""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

from ase.adapters.feeds.http import FeedFetchError, FeedHttpClient, NotModified
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

RANSOMWARE = SourceSpec(
    id="ransomware_live",
    name="Ransomware victim claims (ransomware.live)",
    organisation="ransomware.live",
    category=Category.CYBER,
    kind=SourceKind.API,
    url="https://api.ransomware.live/v2/recentvictims",
    reliability=Reliability.B,
    poll_interval=timedelta(minutes=30),
    licence_note="Personal use; attribute ransomware.live. Victim claims are criminal statements",
    homepage="https://www.ransomware.live/",
)
IODA = SourceSpec(
    id="ioda_outages",
    name="Internet outage alerts (IODA)",
    organisation="Georgia Tech Internet Intelligence Lab (IODA)",
    category=Category.CYBER,
    kind=SourceKind.API,
    url="https://api.ioda.inetintel.cc.gatech.edu/v2/outages/alerts",
    reliability=Reliability.B,
    poll_interval=timedelta(minutes=15),
    licence_note="Academic project; attribute IODA",
    homepage="https://ioda.inetintel.cc.gatech.edu/",
    instrument=True,
)
# Alerts arrive oldest first. A whole-day query fills the 300-row limit before
# recent measurements. Overlap four polls; retained events supply longer views.
LOOKBACK = timedelta(hours=1)
IODA_SEVERITY = {"critical": 0.8, "warning": 0.5}
MAX_ITEMS = 300


def _when(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00").replace(" ", "T"))
        return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)
    except (ValueError, OverflowError):
        return None


def _claim_reference(value: object) -> str | None:
    """Only the clearweb aggregator record is retained, never a criminal leak link."""
    if not isinstance(value, str) or len(value) > 1500:
        return None
    try:
        parts = urlsplit(value)
        if (
            parts.scheme != "https"
            or parts.hostname != "www.ransomware.live"
            or parts.username is not None
            or parts.password is not None
            or parts.port not in (None, 443)
            or not re.fullmatch(r"/id/[A-Za-z0-9_+=-]{1,1024}", parts.path)
        ):
            return None
        return f"https://www.ransomware.live{parts.path}"
    except ValueError:
        return None


class RansomwareConnector:
    spec = RANSOMWARE

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        try:
            data = await self._http.get_json(self.spec.url)
        except NotModified:
            return []
        now = self._clock.now()
        if not isinstance(data, list):
            raise FeedFetchError("Ransomware.live response is not a victim metadata list")
        return [
            event
            for item in data[:MAX_ITEMS]
            if isinstance(item, dict) and (event := self._to_event(item, now))
        ]

    def _to_event(self, item: dict[str, Any], now: datetime) -> Event | None:
        victim = str(item.get("victim") or "").strip()
        group = str(item.get("group") or "").strip()
        if not victim or not group:
            return None
        country = str(item.get("country") or "").strip().upper()
        iso = country if re.fullmatch(r"[A-Z]{2}", country) else None
        page = _claim_reference(item.get("url"))
        key = page.rsplit("/", 1)[-1] if page else f"{victim}@{group}@{item.get('discovered')}"
        activity = str(item.get("activity") or "").strip()
        return Event(
            id=event_id(self.spec.id, key),
            source_id=self.spec.id,
            category=Category.CYBER,
            subtype="ransomware",
            title=f"{victim}: claimed by {group}" + (f" ({activity})" if activity else ""),
            summary=(
                "Unverified victim claim relayed by ransomware.live; no stolen content collected."
            ),
            url=page or self.spec.homepage,
            published_at=_when(item.get("discovered")),
            observed_at=now,
            geo_confidence=GeoConfidence.COUNTRY if iso else GeoConfidence.NONE,
            country_iso=iso,
            tags=frozenset({"ransomware", re.sub(r"[^a-z0-9]+", "_", group.lower()).strip("_")}),
            severity=0.5,
            reliability=self.spec.reliability,
            credibility=Credibility.POSSIBLY_TRUE,
            grade_rationale="A criminal group's own claim, relayed by an aggregator; unverified",
            attributes=freeze_attributes(
                {
                    "victim": victim,
                    "group": group,
                    "sector": activity or None,
                    "domain": str(item.get("domain") or "") or None,
                    "attack_date": str(item.get("attackdate") or "") or None,
                    "date_basis": "Aggregator discovery time; attack/publication time unconfirmed",
                    "geography_basis": "Aggregator-reported victim country; no coordinates",
                    "attribution_status": "Unverified criminal claim",
                }
            ),
            content_hash=content_hash(key, str(item.get("discovered"))),
        )


def _country_of(entity: dict[str, Any]) -> str | None:
    kind = str(entity.get("type") or "")
    code = str(entity.get("code") or "")
    if kind == "country" and re.fullmatch(r"[A-Z]{2}", code):
        return code
    if kind == "geoasn" and "-" in code:
        suffix = code.rsplit("-", 1)[-1]
        return suffix if re.fullmatch(r"[A-Z]{2}", suffix) else None
    return None


class IodaConnector:
    spec = IODA

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        now = self._clock.now()
        since = int((now - LOOKBACK).timestamp())
        url = f"{self.spec.url}?from={since}&until={int(now.timestamp())}&limit={MAX_ITEMS}"
        try:
            data = await self._http.get_json(url, conditional=False)
        except NotModified:
            return []
        if (
            not isinstance(data, dict)
            or data.get("error")
            or not isinstance(data.get("data"), list)
        ):
            raise FeedFetchError("IODA response does not contain a valid alert list")
        items = data["data"]
        return [
            event
            for item in items[:MAX_ITEMS]
            if isinstance(item, dict) and (event := self._to_event(item, now))
        ]

    def _to_event(self, item: dict[str, Any], now: datetime) -> Event | None:
        entity = item.get("entity") or {}
        if not isinstance(entity, dict):
            return None
        level = str(item.get("level") or "").lower()
        if level not in IODA_SEVERITY:
            return None
        kind = str(entity.get("type") or "")
        code = str(entity.get("code") or "")
        if kind not in {"country", "region", "asn", "geoasn"} or not re.fullmatch(
            r"[A-Za-z0-9-]{1,100}", code
        ):
            return None
        name = str(entity.get("name") or code)
        source = str(item.get("datasource") or "signal")
        stamp = item.get("time")
        when = _measurement_time(stamp)
        country = _country_of(entity)
        return Event(
            id=event_id(
                self.spec.id,
                f"{source}-{kind}-{code}-{int(when.timestamp()) if when else 'unknown'}",
            ),
            source_id=self.spec.id,
            category=Category.CYBER,
            subtype="outage",
            title=f"Internet outage signal: {name} ({source}, {level})",
            summary=(
                f"IODA {source} signal for {name} dropped to {item.get('value')} against "
                f"{item.get('historyValue')} ({item.get('condition')})."
            ),
            url=f"https://ioda.inetintel.cc.gatech.edu/{kind}/{code}",
            published_at=when,
            observed_at=now,
            geo_confidence=GeoConfidence.COUNTRY if country else GeoConfidence.NONE,
            country_iso=country,
            tags=frozenset({"outage", source, level, kind}),
            severity=IODA_SEVERITY[level],
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale=(
                "Automated connectivity measurement; cause and attribution not established"
            ),
            attributes=freeze_attributes(
                {
                    "entity_type": kind,
                    "entity_code": code,
                    "datasource": source,
                    "level": level,
                    "value": item.get("value"),
                    "history_value": item.get("historyValue"),
                    "date_basis": "IODA measurement time; unknown when absent or invalid",
                    "attribution_status": "Connectivity signal, not evidence of a cyberattack",
                }
            ),
            content_hash=content_hash(source, kind, code, str(stamp), level),
        )


def _measurement_time(value: object) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    try:
        if not math.isfinite(value):
            return None
        return datetime.fromtimestamp(value, tz=UTC)
    except (ValueError, OverflowError, OSError):
        return None
