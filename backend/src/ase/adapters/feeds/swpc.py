"""NOAA Space Weather Prediction Center: alerts and the current R, S and G scales."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from ase.adapters.feeds.http import FeedHttpClient, NotModified
from ase.application.ports import Clock
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    Reliability,
    content_hash,
    event_id,
    freeze_attributes,
)
from ase.domain.sources import SourceKind, SourceSpec

ALERTS_SPEC = SourceSpec(
    id="noaa_swpc_alerts",
    name="NOAA SWPC space weather alerts",
    organisation="NOAA Space Weather Prediction Center",
    category=Category.SPACE,
    kind=SourceKind.API,
    url="https://services.swpc.noaa.gov/products/alerts.json",
    reliability=Reliability.A,
    poll_interval=timedelta(minutes=5),
    licence_note="US public domain",
    homepage="https://www.swpc.noaa.gov/",
    instrument=True,
)

SCALES_SPEC = SourceSpec(
    id="noaa_swpc_scales",
    name="NOAA SWPC current space weather scales",
    organisation="NOAA Space Weather Prediction Center",
    category=Category.SPACE,
    kind=SourceKind.API,
    url="https://services.swpc.noaa.gov/products/noaa-scales.json",
    reliability=Reliability.A,
    poll_interval=timedelta(minutes=5),
    licence_note="US public domain",
    homepage="https://www.swpc.noaa.gov/noaa-scales-explanation",
    instrument=True,
)

HEADLINE_PREFIXES = ("ALERT", "WARNING", "WATCH", "SUMMARY", "EXTENDED", "CANCEL", "CONTINUED")
MAX_SCALE = 5.0


def _scale(current: dict[str, Any], key: str) -> tuple[str | None, str]:
    """An unavailable NOAA scale is unknown, never an inferred level zero."""
    item = current.get(key)
    if not isinstance(item, dict):
        return None, "unavailable"
    value = item.get("Scale")
    if isinstance(value, bool) or str(value) not in {"0", "1", "2", "3", "4", "5"}:
        return None, "unavailable"
    return str(value), str(item.get("Text") or "description unavailable")


def _parse_issue_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def headline(message: str) -> str | None:
    """The first line of an SWPC bulletin that carries the actual alert text."""
    for line in message.replace("\r", "").split("\n"):
        stripped = line.strip()
        if stripped.upper().startswith(HEADLINE_PREFIXES):
            return stripped
    return None


def _severity_from_text(text: str) -> float:
    for token in text.replace(",", " ").split():
        if len(token) == 2 and token[0] in "GSR" and token[1].isdigit():
            return min(1.0, int(token[1]) / MAX_SCALE)
    return 0.2


class SwpcAlertsConnector:
    spec = ALERTS_SPEC

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        try:
            data = await self._http.get_json(self.spec.url)
        except NotModified:
            return []
        now = self._clock.now()
        items = data if isinstance(data, list) else []
        return [event for item in items if (event := self._to_event(item, now))]

    def _to_event(self, item: dict[str, Any], now: datetime) -> Event | None:
        message = str(item.get("message") or "")
        product = str(item.get("product_id") or "")
        issued = item.get("issue_datetime")
        if not message or not issued:
            return None
        title = headline(message) or f"Space weather bulletin {product}"
        return Event(
            id=event_id(self.spec.id, f"{product}|{issued}"),
            source_id=self.spec.id,
            category=Category.SPACE,
            subtype="space_weather_alert",
            title=title,
            summary=message,
            url=self.spec.homepage,
            published_at=_parse_issue_time(issued) or now,
            observed_at=now,
            tags=frozenset({"space_weather"}),
            severity=_severity_from_text(title),
            reliability=self.spec.reliability,
            credibility=Credibility.CONFIRMED,
            grade_rationale="Official NOAA SWPC bulletin",
            attributes=freeze_attributes({"product_id": product}),
            content_hash=content_hash(product, str(issued), title),
        )


class SwpcScalesConnector:
    spec = SCALES_SPEC

    def __init__(self, http: FeedHttpClient, clock: Clock) -> None:
        self._http = http
        self._clock = clock

    async def fetch(self) -> list[Event]:
        try:
            data = await self._http.get_json(self.spec.url)
        except NotModified:
            return []
        current = data.get("0") if isinstance(data, dict) else None
        if not isinstance(current, dict):
            return []
        now = self._clock.now()
        scales = {key: _scale(current, key) for key in ("R", "S", "G")}
        levels = {key: value[0] for key, value in scales.items()}
        texts = {key: value[1] for key, value in scales.items()}
        stamp = f"{current.get('DateStamp')} {current.get('TimeStamp')}"
        published = _parse_issue_time(stamp) or now
        title = "Space weather now: " + " ".join(
            f"{key}{value if value is not None else ' unknown'}" for key, value in levels.items()
        )
        known = [int(value) for value in levels.values() if value is not None]
        severity = max(known) / MAX_SCALE if known else None
        return [
            Event(
                id=event_id(self.spec.id, "current"),
                source_id=self.spec.id,
                category=Category.SPACE,
                subtype="space_weather_scales",
                title=title,
                summary=f"Radio blackouts {texts['R']}, solar radiation {texts['S']}, "
                f"geomagnetic storms {texts['G']}.",
                url=self.spec.homepage,
                published_at=published,
                observed_at=now,
                tags=frozenset({"space_weather"}),
                severity=severity,
                reliability=self.spec.reliability,
                credibility=Credibility.CONFIRMED,
                grade_rationale="Official NOAA SWPC scales",
                attributes=freeze_attributes(
                    {"r": levels["R"], "s": levels["S"], "g": levels["G"], "stamp": stamp}
                ),
                content_hash=content_hash(*(str(value) for value in levels.values()), stamp),
            )
        ]
