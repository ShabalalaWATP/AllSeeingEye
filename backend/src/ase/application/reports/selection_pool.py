"""The deterministic candidate pool and the retrieval priority applied to it."""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import datetime, timedelta

from ase.application.ports.feeds import EventQuery, EventStore
from ase.domain.country_subjects import matches_country_subject
from ase.domain.events import BoundingBox, Category, Credibility, Event, Reliability
from ase.domain.evidence_time import EvidenceTimeBasis, evidence_time

CREDIBILITY_WEIGHT = {
    Credibility.CONFIRMED: 1.0,
    Credibility.PROBABLY_TRUE: 0.85,
    Credibility.POSSIBLY_TRUE: 0.6,
    Credibility.DOUBTFUL: 0.3,
    Credibility.IMPROBABLE: 0.15,
    Credibility.CANNOT_BE_JUDGED: 0.45,
}
RELIABILITY_WEIGHT = {
    Reliability.A: 1.0,
    Reliability.B: 0.9,
    Reliability.C: 0.7,
    Reliability.D: 0.5,
    Reliability.E: 0.3,
    Reliability.F: 0.5,  # Unknown track record is not a finding of unreliability.
}
MAX_POOL = 4_000


def score(
    event: Event,
    now: datetime,
    window: timedelta,
    time_basis: EvidenceTimeBasis = EvidenceTimeBasis.PUBLICATION,
) -> float:
    """A retrieval priority, never a probability or a report confidence score."""
    timestamp = evidence_time(event, time_basis)
    if timestamp is None and not (
        time_basis is EvidenceTimeBasis.RECORDED and event.project is not None
    ):
        return 0.0
    # Admitted project-year intervals have no exact instant. Use neutral recency,
    # retaining relevance and source weights without inventing a publication date.
    age_hours = 0.0 if timestamp is None else max(0.0, (now - timestamp).total_seconds() / 3600)
    recency = math.exp(-age_hours / max(1.0, window.total_seconds() / 3600))
    severity = 1.0 + (event.severity or 0.0) * 0.5
    return (
        CREDIBILITY_WEIGHT[event.credibility] * RELIABILITY_WEIGHT[event.reliability]
        * recency
        * severity
    )  # fmt: skip


def candidate_pool(
    store: EventStore,
    categories: frozenset[Category],
    since: datetime,
    country_iso: str | None,
    bbox: BoundingBox | None,
    countries: Sequence[str],
    time_basis: EvidenceTimeBasis,
    until: datetime | None,
    include_unknown_dates: bool,
    include_country_subjects: bool = False,
) -> list[Event]:
    """Query selected scopes without a global fallback, under one aggregate pool cap."""
    scopes = [(country_iso, bbox)] if bbox is not None or country_iso or not countries else []
    scopes.extend((iso, None) for iso in dict.fromkeys(countries) if iso != country_iso)
    per_scope = max(1, MAX_POOL // len(scopes))
    queries = [
        EventQuery(
            categories=categories,
            country_iso=iso,
            bbox=bounds,
            since=since,
            limit=per_scope,
            time_basis=time_basis,
            until=until,
            include_unknown_dates=include_unknown_dates,
        )
        for iso, bounds in scopes
    ]
    seen: dict[str, Event] = {}
    for query in queries:
        for event in store.query(query):
            seen.setdefault(event.id, event)
    selected_countries = tuple(
        dict.fromkeys((*(countries or ()), *((country_iso,) if country_iso else ())))
    )
    if include_country_subjects and selected_countries and bbox is None:
        # This opt-in is only used on a report's bounded private pool. Fresh RSS
        # items carry app-produced exact-span hints; retained live rows do not.
        candidates = store.query(
            EventQuery(
                categories=categories,
                since=since,
                until=until,
                time_basis=time_basis,
                limit=MAX_POOL,
            )
        )
        for event in candidates:
            if len(seen) >= MAX_POOL:
                break
            if matches_country_subject(event, selected_countries):
                seen.setdefault(event.id, event)
    return list(seen.values())[:MAX_POOL]
