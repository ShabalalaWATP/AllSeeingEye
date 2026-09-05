"""Cyber feeds: ransomware victim claims (ransomware.live) and internet outage alerts (IODA).

Both are country-level, so events carry a country code without coordinates and the
pipeline places them at the nation's centroid with country-level geo confidence.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from ase.adapters.feeds.http import FeedHttpClient, NotModified
from ase.application.feeds.pipeline import strip_html
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
LOOKBACK = timedelta(hours=24)
IODA_SEVERITY = {"critical": 0.8, "warning": 0.5}
MAX_ITEMS = 300


def _when(value: object, fallback: datetime) -> datetime:
    if not isinstance(value, str):
        return fallback
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00").replace(" ", "T"))
    except ValueError:
        return fallback
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)


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
        items = [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []
        return [event for item in items[:MAX_ITEMS] if (event := self._to_event(item, now))]

    def _to_event(self, item: dict[str, Any], now: datetime) -> Event | None:
        victim = str(item.get("victim") or "").strip()
        group = str(item.get("group") or "").strip()
        if not victim or not group:
            return None
        country = str(item.get("country") or "").strip().upper()
        iso = country if re.fullmatch(r"[A-Z]{2}", country) else None
        page = str(item.get("url") or "")
        key = page.rsplit("/", 1)[-1] if page else f"{victim}@{group}"
        activity = str(item.get("activity") or "").strip()
        return Event(
            id=event_id(self.spec.id, key),
            source_id=self.spec.id,
            category=Category.CYBER,
            subtype="ransomware",
            title=f"{victim}: claimed by {group}" + (f" ({activity})" if activity else ""),
            summary=(strip_html(str(item.get("description") or "")) or "")[:2_000] or None,
            url=page or self.spec.homepage,
            published_at=_when(item.get("discovered"), now),
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
                    "domain": item.get("domain") or None,
                    "attack_date": item.get("attackdate"),
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
        items = data.get("data", []) if isinstance(data, dict) else []
        return [
            event
            for item in items
            if isinstance(item, dict) and (event := self._to_event(item, now))
        ]

    def _to_event(self, item: dict[str, Any], now: datetime) -> Event | None:
        entity = item.get("entity") or {}
        level = str(item.get("level") or "").lower()
        if level not in IODA_SEVERITY:
            return None
        kind = str(entity.get("type") or "")
        code = str(entity.get("code") or "")
        name = str(entity.get("name") or code)
        source = str(item.get("datasource") or "signal")
        stamp = item.get("time")
        when = datetime.fromtimestamp(int(stamp), tz=UTC) if isinstance(stamp, int | float) else now
        country = _country_of(entity)
        return Event(
            id=event_id(self.spec.id, f"{source}-{kind}-{code}-{int(when.timestamp())}"),
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
            grade_rationale="Automated measurement from several vantage points",
            attributes=freeze_attributes(
                {
                    "entity_type": kind,
                    "entity_code": code,
                    "datasource": source,
                    "level": level,
                    "value": item.get("value"),
                    "history_value": item.get("historyValue"),
                }
            ),
            content_hash=content_hash(source, kind, code, str(stamp), level),
        )
