"""Scope selection for public reporting versus explicitly supplied private inputs."""

from collections.abc import Mapping
from dataclasses import replace

from ase.application.ports.feeds import EventStore
from ase.application.reports.depth import depth_for
from ase.application.reports.production_types import Job
from ase.application.reports.reused_evidence import with_reused_evidence
from ase.application.reports.selection import Selection, select_evidence
from ase.application.reports.subscription_updates import previous_signatures
from ase.domain.direction import Direction
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.grading import SourceProfile
from ase.domain.research import ResearchFocus, ResearchQuery


def select_for_job(
    store: EventStore,
    profiles: Mapping[str, SourceProfile],
    job: Job,
    direction: Direction | None,
    extra_terms: tuple[str, ...] = (),
    *,
    runtime_query: ResearchQuery | None = None,
) -> Selection:
    private = job.request.research_focus in (ResearchFocus.DOCUMENT, ResearchFocus.MEDIA)
    area = job.request.effective_area is not None
    window = int(job.window.total_seconds() // 3600)
    if private and job.seed_events:
        # A supplied historic document is relevant because it was explicitly supplied,
        # not because its publication date fits a current news window. Preserve its date.
        dates = [item.published_at for item in job.seed_events if item.published_at is not None]
        if dates:
            earliest = min(dates)
            window = max(window, int((job.now - earliest).total_seconds() // 3600) + 1)
    strategy = replace(
        job.template.strategy,
        window_hours=window,
        categories=frozenset() if private else job.template.strategy.categories,
    )
    depth = depth_for(job.request.research_mode)
    if depth is not None:
        strategy = replace(
            strategy, max_items=depth.evidence_items, per_source_cap=depth.per_source_cap
        )
    if private:
        # Private sections are parts of one supplied input, not competing publishers.
        # A diversity cap would discard later photographs, contradictions and caveats.
        # Preserve the complete bounded assessment within the report's 100-item ceiling;
        # original grades and the lack of independent corroboration remain unchanged.
        strategy = replace(strategy, max_items=100, per_source_cap=100)
    selected = select_evidence(
        store,
        profiles,
        strategy,
        now=job.now,
        country_iso=None if private else job.request.country_iso,
        categories=() if private else job.request.categories,
        terms=(
            *(direction.search_terms if direction else job.terms),
            *extra_terms,
            *(
                term
                for task in (
                    runtime_query.planned_tasks
                    if runtime_query is not None
                    else job.request.research_planned_tasks
                )
                for term in task.terms
            ),
        ),
        # Area eligibility was admitted by spatial providers. A point-only filter
        # here would silently discard valid footprints without event coordinates.
        bbox=None if private or area else job.bbox,
        countries=()
        if private
        else tuple(dict.fromkeys((*job.request.country_isos, *job.countries))),
        hazard=None if private else job.hazard,
        time_basis=job.request.effective_time_basis,
        since=job.period_from if job.request.research_since is not None else None,
        until=job.period_to if job.request.research_until is not None else None,
        include_unknown_dates=private,
        include_country_subjects=(
            job.request.research_mode is not None
            and job.request.research_focus is ResearchFocus.GENERAL
            and not area
            and job.bbox is None
            and not job.countries
            and bool(job.request.country_isos)
            and job.request.effective_time_basis is not EvidenceTimeBasis.RECORDED
        ),
        seen_content_signatures=(
            previous_signatures(job.subscription_baseline)
            | frozenset(job.request.subscription_seen_signatures)
        ),
    )
    return with_reused_evidence(selected, job.reused_evidence)
