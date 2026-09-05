"""Humanitarian context feeds: WHO Disease Outbreak News and IFRC GO emergencies.

Neither carries coordinates, so these events sit in the store and the trackers rather
than on the globe; the country code lets the nation filter and the briefs find them.
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

WHO_DON = SourceSpec(
    id="who_don",
    name="WHO Disease Outbreak News",
    organisation="World Health Organization",
    category=Category.HUMANITARIAN,
    kind=SourceKind.API,
    url="https://www.who.int/api/news/diseaseoutbreaknews?$orderby=PublicationDate%20desc&$top=30",
    reliability=Reliability.A,
    poll_interval=timedelta(hours=1),
    licence_note="WHO terms; cite WHO",
    homepage="https://www.who.int/emergencies/disease-outbreak-news",
)
IFRC_GO = SourceSpec(
    id="ifrc_go",
    name="IFRC GO emergencies",
    organisation="International Federation of Red Cross and Red Crescent Societies",
    category=Category.HUMANITARIAN,
    kind=SourceKind.API,
    url="https://goadmin.ifrc.org/api/v2/event/?limit=50&ordering=-disaster_start_date",
    reliability=Reliability.B,
    poll_interval=timedelta(hours=1),
    licence_note="IFRC GO public data; licence not stated",
    homepage="https://go.ifrc.org/",
)
IFRC_SEVERITY = {"0": 0.3, "1": 0.6, "2": 0.9}


def _when(value: object, fallback: datetime) -> datetime:
    if not isinstance(value, str):
        return fallback
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return fallback
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)).astimezone(UTC)


class WhoOutbreakConnector:
    spec = WHO_DON

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        try:
            data = await self._http.get_json(self.spec.url)
        except NotModified:
            return []
        now = self._clock.now()
        items = data.get("value", []) if isinstance(data, dict) else []
        return [event for item in items if (event := self._to_event(item, now))]

    def _to_event(self, item: dict[str, Any], now: datetime) -> Event | None:
        slug = str(item.get("UrlName") or "")
        title = str(item.get("Title") or "").strip()
        if not slug or not title:
            return None
        published = _when(item.get("PublicationDate"), now)
        return Event(
            id=event_id(self.spec.id, slug),
            source_id=self.spec.id,
            category=Category.HUMANITARIAN,
            subtype="outbreak",
            title=title[:300],
            summary=(strip_html(str(item.get("Summary") or "")) or "")[:2_000] or None,
            url=f"https://www.who.int/emergencies/disease-outbreak-news/item/{slug}",
            published_at=published,
            observed_at=now,
            geo_confidence=GeoConfidence.NONE,
            tags=frozenset({"outbreak"}),
            severity=0.5,
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="Official WHO notification",
            attributes=freeze_attributes({"slug": slug}),
            content_hash=content_hash(slug, str(item.get("PublicationDate"))),
        )


class IfrcGoConnector:
    spec = IFRC_GO

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        try:
            data = await self._http.get_json(self.spec.url)
        except NotModified:
            return []
        now = self._clock.now()
        items = data.get("results", []) if isinstance(data, dict) else []
        return [event for item in items if (event := self._to_event(item, now))]

    def _to_event(self, item: dict[str, Any], now: datetime) -> Event | None:
        emergency_id = item.get("id")
        name = re.sub(r"\s+", " ", str(item.get("name") or "")).strip()
        if emergency_id is None or not name:
            return None
        kind = str((item.get("dtype") or {}).get("name") or "Emergency")
        countries = [
            str(country.get("iso")).upper()
            for country in item.get("countries") or []
            if country.get("iso")
        ]
        level = str(item.get("ifrc_severity_level") or "0")
        display = str(item.get("ifrc_severity_level_display") or "").lower()
        return Event(
            id=event_id(self.spec.id, str(emergency_id)),
            source_id=self.spec.id,
            category=Category.HUMANITARIAN,
            subtype="emergency",
            title=name[:300],
            summary=(strip_html(str(item.get("summary") or "")) or "")[:2_000] or None,
            url=f"https://go.ifrc.org/emergencies/{emergency_id}",
            published_at=_when(item.get("disaster_start_date"), now),
            observed_at=now,
            geo_confidence=GeoConfidence.COUNTRY if countries else GeoConfidence.NONE,
            country_iso=countries[0] if countries else None,
            tags=frozenset(
                {"emergency", re.sub(r"[^a-z0-9]+", "_", kind.lower()).strip("_")}
                | ({display} if display else set())
            ),
            severity=IFRC_SEVERITY.get(level, 0.3),
            reliability=self.spec.reliability,
            credibility=Credibility.PROBABLY_TRUE,
            grade_rationale="Emergency record kept by the national societies and the IFRC",
            attributes=freeze_attributes(
                {
                    "disaster_type": kind,
                    "countries": ", ".join(countries),
                    "severity_level": display or level,
                    "glide": item.get("glide") or None,
                    "affected": item.get("num_affected"),
                }
            ),
            content_hash=content_hash(str(emergency_id), level, name),
        )
