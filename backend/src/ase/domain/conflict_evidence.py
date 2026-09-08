"""Conservative conflict-report grouping, occurrence dates and casualty estimates."""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ase.domain.events import Category, Event

VIOLENCE_TYPES = frozenset(
    {
        "fight",
        "battle",
        "armed_clash",
        "organised_violence",
        "strike",
        "explosion",
        "civilian_harm",
        "violence_against_civilians",
        "mass_violence",
    }
)
CONTEXT_CATEGORIES = frozenset({Category.NEWS, Category.POLITICAL, Category.HUMANITARIAN})
_CONTEXT = re.compile(
    r"\b(war|conflict|military|army|troops|strike|attack|shelling|battle|clash|"
    r"ceasefire|peace|talks|negotiations|refugees|displacement|humanitarian|sanctions)\b",
    re.I,
)
_DATED_SOURCES = frozenset({"gdelt_events", "ucdp_candidate", "acled_events"})


def is_violence(event: Event) -> bool:
    return event.category is Category.CONFLICT and event.subtype in VIOLENCE_TYPES


def is_conflict_context(event: Event) -> bool:
    return event.category in CONTEXT_CATEGORIES and (
        bool(_CONTEXT.search(f"{event.title_en or event.title} {event.summary or ''}"))
    )


def occurrence_time(event: Event) -> datetime | None:
    # Week/month estimates cannot support exact daily or seven-day counts.
    precision = event.attributes.get("date_precision", event.attributes.get("time_precision"))
    if event.source_id in {"ucdp_candidate", "acled_events"} and precision not in (None, 1, "1"):
        return None
    start, end = event.attributes.get("occurrence_start"), event.attributes.get("occurrence_end")
    if start and end and str(start)[:10] != str(end)[:10]:
        return None
    value = event.attributes.get("occurrence_start", event.attributes.get("event_day"))
    if value is not None:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
        except ValueError:
            return None
    if event.source_id in _DATED_SOURCES or "machine_coded" in event.tags:
        return None
    return event.published_at


def canonical_report_url(value: str | None) -> str | None:
    if not value:
        return None
    try:
        url = urlsplit(value)
        if url.scheme not in ("https", "http") or not url.hostname or url.username or url.password:
            return None
        query = [(k, v) for k, v in parse_qsl(url.query) if not k.lower().startswith("utm_")]
        return urlunsplit((url.scheme, url.netloc.lower(), url.path, urlencode(sorted(query)), ""))
    except ValueError:
        return None


def _evidence_key(event: Event) -> tuple[object, ...]:
    # Cross-source IDs are usable only with an explicitly declared originating dataset.
    origin, identifier = event.attributes.get("origin_dataset"), event.attributes.get("incident_id")
    if isinstance(origin, str) and isinstance(identifier, str) and origin and identifier:
        return ("dataset", origin, identifier)
    when, url = occurrence_time(event), canonical_report_url(event.url)
    if when is None or url is None:
        return ("record", event.id)
    point = (event.point.lon, event.point.lat) if event.point else None
    # Same article can describe several incidents: keep date, exact geography, type
    # and actors in the key. Text similarity alone never merges incidents.
    return (
        "report",
        url,
        when.isoformat(),
        event.subtype,
        point,
        str(event.attributes.get("actor1") or ""),
        str(event.attributes.get("actor2") or ""),
    )


def evidence_groups(events: Iterable[Event]) -> list[tuple[Event, ...]]:
    groups: dict[tuple[object, ...], list[Event]] = {}
    seen: set[str] = set()
    for event in events:
        if event.id not in seen:
            groups.setdefault(_evidence_key(event), []).append(event)
            seen.add(event.id)
    return [tuple(group) for group in groups.values()]


def _count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return int(value) if math.isfinite(value) and value >= 0 and value == int(value) else None


@dataclass(frozen=True)
class CasualtySummary:
    lower: int | None
    upper: int | None
    unknown_incidents: int
    disputed_incidents: int


def casualties(groups: Iterable[tuple[Event, ...]]) -> CasualtySummary:
    lower = upper = known = unknown = disputed = 0
    for group in groups:
        estimates: set[tuple[int, int]] = set()
        for event in group:
            attrs = event.attributes
            best = _count(attrs.get("reported_fatalities_best", attrs.get("fatalities")))
            if best == 0 and attrs.get("fatalities_uncertain_zero") is True:
                continue
            low = _count(attrs.get("reported_fatalities_low", attrs.get("fatalities_low", best)))
            high = _count(attrs.get("reported_fatalities_high", attrs.get("fatalities_high", best)))
            low = best if low is None else low
            high = best if high is None else high
            if low is not None and high is not None and low <= high:
                estimates.add((low, high))
        if not estimates:
            unknown += 1
            continue
        known += 1
        lower += min(pair[0] for pair in estimates)
        upper += max(pair[1] for pair in estimates)
        disputed += len(estimates) > 1
    return CasualtySummary(lower if known else None, upper if known else None, unknown, disputed)
