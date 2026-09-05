"""Evidence selection: relevance, grade, recency and diversity inside the token budget."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.reports.templates import EvidenceStrategy
from ase.domain.events import Category, Credibility, Event, Reliability
from ase.domain.evidence import EvidenceItem, injection_flags
from ase.domain.grading import SourceProfile

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
    Reliability.F: 0.3,
}
MAX_POOL = 4_000


@dataclass(frozen=True, slots=True)
class Selection:
    items: tuple[EvidenceItem, ...]
    flagged: int
    considered: int


def score(event: Event, now: datetime, window: timedelta) -> float:
    age_hours = max(0.0, (now - event.published_at).total_seconds() / 3600)
    recency = math.exp(-age_hours / max(1.0, window.total_seconds() / 3600))
    severity = 1.0 + (event.severity or 0.0) * 0.5
    return (
        CREDIBILITY_WEIGHT[event.credibility] * RELIABILITY_WEIGHT[event.reliability]
        * recency
        * severity
    )  # fmt: skip


def select_evidence(
    store: EventStore,
    profiles: Mapping[str, SourceProfile],
    strategy: EvidenceStrategy,
    *,
    now: datetime,
    country_iso: str | None = None,
    categories: Sequence[Category] = (),
) -> Selection:
    """Freeze the best evidence for the scope; items with instruction-like text are left out."""
    window = timedelta(hours=strategy.window_hours)
    wanted = frozenset(categories) or strategy.categories
    pool = store.query(
        EventQuery(
            categories=wanted,
            country_iso=country_iso,
            since=now - window,
            limit=MAX_POOL,
        )
    )
    ranked = sorted(pool, key=lambda event: score(event, now, window), reverse=True)
    per_source: dict[str, int] = {}
    chosen: list[EvidenceItem] = []
    flagged = 0
    for event in ranked:
        if len(chosen) >= strategy.max_items:
            break
        if per_source.get(event.source_id, 0) >= strategy.per_source_cap:
            continue
        if injection_flags(event.title, event.summary):
            flagged += 1
            continue
        profile = profiles.get(event.source_id)
        per_source[event.source_id] = per_source.get(event.source_id, 0) + 1
        chosen.append(
            EvidenceItem.from_event(
                f"E{len(chosen) + 1}",
                event,
                now,
                source_name=profile.name if profile else event.source_id,
                independence_key=profile.independence_key if profile else event.source_id,
                instrument=profile.instrument if profile else False,
                flags=sorted(
                    (profile.flags if profile else frozenset())
                    | event.tags & {"state_controlled", "interested_party"}
                ),
            )
        )
    return Selection(items=tuple(chosen), flagged=flagged, considered=len(pool))
