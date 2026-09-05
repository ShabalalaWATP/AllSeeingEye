"""Builders and fakes for the fusion core tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ase.adapters.feeds.http import NotModified
from ase.domain.events import (
    Category,
    Credibility,
    Event,
    GeoConfidence,
    Point,
    Reliability,
    content_hash,
    event_id,
)
from ase.domain.sources import SourceKind, SourceSpec
from helpers import FakeClock

__all__ = [
    "NOW",
    "FakeClock",
    "FakeConnector",
    "FakeHttp",
    "load_fixture",
    "make_event",
    "make_spec",
]

FIXTURES = Path(__file__).parent / "fixtures" / "feeds"
NOW = datetime(2026, 9, 5, 0, 0, tzinfo=UTC)
DEFAULT_POINT = Point(lon=10.0, lat=50.0)


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text("utf-8"))


def make_event(
    key: str = "e1",
    *,
    source_id: str = "test_source",
    category: Category = Category.DISASTER,
    subtype: str = "earthquake",
    title: str = "Test event",
    published_at: datetime = NOW,
    observed_at: datetime = NOW,
    point: Point | None = DEFAULT_POINT,
    country_iso: str | None = None,
    summary: str | None = "A summary",
    severity: float | None = 0.5,
    version: int = 1,
) -> Event:
    return Event(
        id=event_id(source_id, key),
        source_id=source_id,
        category=category,
        subtype=subtype,
        title=title,
        summary=summary,
        url=f"https://example.com/{key}",
        published_at=published_at,
        observed_at=observed_at,
        point=point,
        geo_confidence=GeoConfidence.EXACT if point else GeoConfidence.NONE,
        country_iso=country_iso,
        tags=frozenset({subtype}),
        severity=severity,
        reliability=Reliability.A,
        credibility=Credibility.PROBABLY_TRUE,
        grade_rationale="test",
        content_hash=content_hash(key, str(version)),
    )


def make_spec(source_id: str = "test_source", seconds: int = 60) -> SourceSpec:
    return SourceSpec(
        id=source_id,
        name="Test source",
        organisation="Test Org",
        category=Category.DISASTER,
        kind=SourceKind.API,
        url="https://feeds.test/events.json",
        reliability=Reliability.A,
        poll_interval=timedelta(seconds=seconds),
    )


class FakeConnector:
    def __init__(self, spec: SourceSpec | None = None, events: list[Event] | None = None) -> None:
        self.spec = spec or make_spec()
        self.events = events if events is not None else [make_event()]
        self.failures = 0
        self.calls = 0

    async def fetch(self) -> list[Event]:
        self.calls += 1
        if self.failures > 0:
            self.failures -= 1
            msg = "upstream exploded"
            raise RuntimeError(msg)
        return list(self.events)


class FakeHttp:
    """Stands in for FeedHttpClient: serves fixtures by URL or raises."""

    def __init__(self, payloads: dict[str, Any] | None = None, not_modified: bool = False) -> None:
        self.payloads = payloads or {}
        self.not_modified = not_modified
        self.requests: list[str] = []

    async def get_json(self, url: str, *, conditional: bool = True) -> Any:
        self.requests.append(url)
        if self.not_modified:
            raise NotModified(url)
        for key, payload in self.payloads.items():
            if key in url:
                return payload
        msg = f"no fixture for {url}"
        raise KeyError(msg)

    async def get_text(self, url: str, *, conditional: bool = True) -> str:
        self.requests.append(url)
        if self.not_modified:
            raise NotModified(url)
        for key, payload in self.payloads.items():
            if key in url:
                return str(payload)
        msg = f"no fixture for {url}"
        raise KeyError(msg)

    async def get_bytes(self, url: str, *, conditional: bool = True) -> bytes:
        self.requests.append(url)
        if self.not_modified:
            raise NotModified(url)
        for key, payload in self.payloads.items():
            if key in url:
                return payload if isinstance(payload, bytes) else str(payload).encode("utf-8")
        msg = f"no fixture for {url}"
        raise KeyError(msg)
