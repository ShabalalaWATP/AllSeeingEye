"""Evidence selection: relevance, grade, recency and diversity inside the token budget."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.reports.selection_choice import choose_items, diversify, term_presence
from ase.application.reports.subscription_updates import content_signature
from ase.application.reports.templates import EvidenceStrategy
from ase.domain.country_subjects import matches_country_subject
from ase.domain.events import BoundingBox, Category, Credibility, Event, Reliability
from ase.domain.evidence import EvidenceItem, injection_flags
from ase.domain.evidence_clusters import duplicate_clusters
from ase.domain.evidence_time import EvidenceTimeBasis, evidence_time
from ase.domain.grading import SourceProfile
from ase.domain.project import project_to_dict
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
    merged: int = 0


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


def term_matches(event: Event, terms: Sequence[str]) -> int:
    """Match original and translated titles without replacing the source material."""
    return term_presence(event, terms)


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


def select_evidence(
    store: EventStore,
    profiles: Mapping[str, SourceProfile],
    strategy: EvidenceStrategy,
    *,
    now: datetime,
    country_iso: str | None = None,
    categories: Sequence[Category] = (),
    terms: Sequence[str] = (),
    term_groups: Sequence[Sequence[str]] = (),
    bbox: BoundingBox | None = None,
    countries: Sequence[str] = (),
    hazard: Hazard | None = None,
    time_basis: EvidenceTimeBasis = EvidenceTimeBasis.PUBLICATION,
    until: datetime | None = None,
    since: datetime | None = None,
    include_unknown_dates: bool = False,
    include_country_subjects: bool = False,
    seen_content_signatures: frozenset[str] = frozenset(),
) -> Selection:
    """Freeze the best evidence for the scope; items with instruction-like text are left out.

    Earlier term groups take precedence. Matches within a group are ordered by
    evidence score and stable ID; unmatched items fill the remaining places.
    A bounding box and extra countries widen the pool (a
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
        include_country_subjects,
    )
    if hazard is not None:
        pool = [event for event in pool if hazard_of(event) is hazard]
    lowered_groups = tuple(
        tuple(term.lower().strip() for term in group if term.strip())
        for group in (term_groups or (terms,))
    )
    lowered = tuple(dict.fromkeys(term for group in lowered_groups for term in group))

    def relevance(event: Event) -> int:
        return next(
            (index for index, group in enumerate(lowered_groups) if term_matches(event, group)),
            len(lowered_groups),
        )

    def rank(event: Event) -> tuple[int, float, str]:
        group = group_index[event.id]
        matches = term_matches(event, lowered_groups[group]) if group < len(lowered_groups) else 0
        return (
            group,
            -score(
                event, until if since is not None and until is not None else now, window, time_basis
            )
            * (1 + 0.25 * matches),
            event.id,
        )

    safe = [
        event
        for event in pool
        if not injection_flags(
            event.title,
            event.title_en,
            event.summary,
            *(value for value in project_to_dict(event.project).values() if isinstance(value, str))
            if event.project is not None
            else (),
        )
    ]
    group_index = {event.id: relevance(event) for event in safe}
    ordered = sorted(safe, key=rank)
    buckets: list[list[Event]] = [[] for _ in range(len(lowered_groups) + 1)]
    for event in ordered:
        buckets[group_index[event.id]].append(event)
    ranked = [event for bucket in buckets for event in diversify(bucket, profiles, lowered)]
    if seen_content_signatures:
        # Preserve relevance ahead of novelty, and quality/diversity within each group.
        # Repeated items may still supply essential context after new relevant evidence.
        ranked.sort(
            key=lambda event: (
                group_index[event.id],
                content_signature(event) in seen_content_signatures,
            )
        )
    clusters, cluster_reasons = duplicate_clusters(safe)
    chosen = choose_items(
        ranked,
        profiles,
        strategy,
        now=now,
        clusters=clusters,
        cluster_reasons=cluster_reasons,
    )
    return Selection(
        items=chosen.items,
        flagged=len(pool) - len(safe),
        considered=len(pool),
        merged=chosen.merged,
    )
