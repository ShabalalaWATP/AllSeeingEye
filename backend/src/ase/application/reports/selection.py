"""Evidence selection: relevance, grade, recency and diversity inside the token budget."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.reports.templates import EvidenceStrategy
from ase.domain.events import BoundingBox, Category, Credibility, Event, Reliability
from ase.domain.evidence import EvidenceItem, injection_flags
from ase.domain.evidence_time import EvidenceTimeBasis, evidence_time
from ase.domain.grading import SourceProfile
from ase.domain.source_ratings import unassessed_source_rating
from ase.domain.trackers import Hazard, hazard_of

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


@dataclass(frozen=True, slots=True)
class Selection:
    items: tuple[EvidenceItem, ...]
    flagged: int
    considered: int


def score(
    event: Event,
    now: datetime,
    window: timedelta,
    time_basis: EvidenceTimeBasis = EvidenceTimeBasis.PUBLICATION,
) -> float:
    """A retrieval priority, never a probability or a report confidence score."""
    timestamp = evidence_time(event, time_basis)
    if timestamp is None:
        return 0.0
    age_hours = max(0.0, (now - timestamp).total_seconds() / 3600)
    recency = math.exp(-age_hours / max(1.0, window.total_seconds() / 3600))
    severity = 1.0 + (event.severity or 0.0) * 0.5
    return (
        CREDIBILITY_WEIGHT[event.credibility] * RELIABILITY_WEIGHT[event.reliability]
        * recency
        * severity
    )  # fmt: skip


def term_matches(event: Event, terms: Sequence[str]) -> int:
    """Match original and translated titles without replacing the source material."""
    if not terms:
        return 0
    text = f"{event.title} {event.title_en or ''} {event.summary or ''}".lower()
    return sum(1 for term in terms if term in text)


def _pool(
    store: EventStore,
    categories: frozenset[Category],
    since: datetime,
    country_iso: str | None,
    bbox: BoundingBox | None,
    countries: Sequence[str],
    time_basis: EvidenceTimeBasis,
    until: datetime | None,
    include_unknown_dates: bool,
) -> list[Event]:
    """One query for the box or country, one per extra country, merged by event id."""
    queries = [
        EventQuery(
            categories=categories,
            country_iso=country_iso,
            bbox=bbox,
            since=since,
            limit=MAX_POOL,
            time_basis=time_basis,
            until=until,
            include_unknown_dates=include_unknown_dates,
        )
    ]
    queries.extend(
        EventQuery(
            categories=categories,
            country_iso=iso,
            since=since,
            limit=MAX_POOL,
            time_basis=time_basis,
            until=until,
            include_unknown_dates=include_unknown_dates,
        )
        for iso in countries
        if iso != country_iso
    )
    seen: dict[str, Event] = {}
    for query in queries:
        for event in store.query(query):
            seen.setdefault(event.id, event)
    return list(seen.values())


def _organisation(event: Event, profiles: Mapping[str, SourceProfile]) -> tuple[str, str]:
    profile = profiles.get(event.source_id)
    if profile is not None and profile.independence_key:
        return ("organisation", profile.independence_key)
    return ("connector", event.source_id)


def _diversify(
    ranked: Sequence[Event], profiles: Mapping[str, SourceProfile], terms: Sequence[str]
) -> list[Event]:
    """Prefer varied reporting, then backfill without discarding possible counterevidence.

    Matching evidence stays ahead of unmatched context. Within either tier, the first
    pass takes one item per declared organisation and defers equal titles or hashes.
    This is a bounded retrieval heuristic, not proof of independent sourcing. Deferred
    items remain available when the pool is thin, including similar opposing reports.
    """
    result: list[Event] = []
    for matching in (True, False):
        organisations: set[tuple[str, str]] = set()
        titles: set[str] = set()
        hashes: set[str] = set()
        deferred: list[Event] = []
        for event in ranked:
            if bool(term_matches(event, terms)) != matching:
                continue
            organisation = _organisation(event, profiles)
            title = " ".join((event.title_en or event.title).casefold().split())
            copied = (bool(title) and title in titles) or (
                bool(event.content_hash) and event.content_hash in hashes
            )
            if organisation in organisations or copied:
                deferred.append(event)
                continue
            organisations.add(organisation)
            if title:
                titles.add(title)
            if event.content_hash:
                hashes.add(event.content_hash)
            result.append(event)
        result.extend(deferred)
    return result


def select_evidence(
    store: EventStore,
    profiles: Mapping[str, SourceProfile],
    strategy: EvidenceStrategy,
    *,
    now: datetime,
    country_iso: str | None = None,
    categories: Sequence[Category] = (),
    terms: Sequence[str] = (),
    bbox: BoundingBox | None = None,
    countries: Sequence[str] = (),
    hazard: Hazard | None = None,
    time_basis: EvidenceTimeBasis = EvidenceTimeBasis.PUBLICATION,
    until: datetime | None = None,
    since: datetime | None = None,
    include_unknown_dates: bool = False,
) -> Selection:
    """Freeze the best evidence for the scope; items with instruction-like text are left out.

    Search terms (from the direction call or a conflict's keywords) put matching items
    ahead of the rest and boost them by the number of terms matched; unmatched items only
    fill the remaining places. A bounding box and extra countries widen the pool (a
    conflict area); a hazard narrows it to one kind of disaster.
    """
    window = (
        (until - since)
        if since is not None and until is not None
        else timedelta(hours=strategy.window_hours)
    )
    wanted = frozenset(categories) or strategy.categories
    pool = _pool(
        store,
        wanted,
        since if since is not None else now - window,
        country_iso,
        bbox,
        countries,
        time_basis,
        until,
        include_unknown_dates,
    )
    if hazard is not None:
        pool = [event for event in pool if hazard_of(event) is hazard]
    lowered = tuple(term.lower().strip() for term in terms if term.strip())

    def rank(event: Event) -> tuple[int, float, str]:
        matches = term_matches(event, lowered)
        return (
            -bool(matches),
            -score(
                event, until if since is not None and until is not None else now, window, time_basis
            )
            * (1 + 0.25 * matches),
            event.id,
        )

    safe = [
        event for event in pool if not injection_flags(event.title, event.title_en, event.summary)
    ]
    ranked = _diversify(sorted(safe, key=rank), profiles, lowered)
    per_organisation: dict[tuple[str, str], int] = {}
    chosen: list[EvidenceItem] = []
    for event in ranked:
        if len(chosen) >= strategy.max_items:
            break
        organisation = _organisation(event, profiles)
        if per_organisation.get(organisation, 0) >= strategy.per_source_cap:
            continue
        profile = profiles.get(event.source_id)
        per_organisation[organisation] = per_organisation.get(organisation, 0) + 1
        chosen.append(
            EvidenceItem.from_event(
                f"E{len(chosen) + 1}",
                event,
                now,
                source_name=profile.name if profile else event.source_id,
                independence_key=profile.independence_key if profile else "",
                instrument=profile.instrument if profile else False,
                source_rating=profile.rating if profile else unassessed_source_rating(),
                flags=sorted(
                    (profile.flags if profile else frozenset())
                    | event.tags & {"state_controlled", "interested_party"}
                ),
            )
        )
    return Selection(items=tuple(chosen), flagged=len(pool) - len(safe), considered=len(pool))
