"""Assemble the geography receipt that travels with one report version.

Three honest statements and nothing else: where the scope came from, how much of the
selected evidence is genuinely located inside it, and whether any recorded baseline
exists to say if activity is normal. Where no baseline exists, this says so instead of
inventing one. No model call, no network request and no new stored row.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import timedelta

from ase.application.ports.area_geography import AreaGeography, EvidencePlacement, ScopeRequest
from ase.application.ports.baselines import BaselineRepository
from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.ports.interference import InterferenceCells
from ase.application.reports.area_instruments import eligible_instruments, sweep_instruments
from ase.application.reports.production_types import Job
from ase.application.reports.selection import Selection
from ase.domain.area_assets import AssetClass, asset_triggers, trigger_text
from ase.domain.area_context import NO_BASELINE, AreaContext, BaselineComparison
from ase.domain.area_instruments import NO_INSTRUMENTS
from ase.domain.aviation import military_by_country
from ase.domain.events import Category
from ase.domain.evidence import EvidenceItem
from ase.domain.research import ResearchQuery
from ase.domain.research_records import ResearchReceipt

BASELINE_DAYS = 30
BASELINE_KIND = "military_aircraft"
MAX_BASELINE_COUNTRIES = 4
AVIATION_POOL = 20_000
MILITARY_BASIS = (
    "Hourly samples of aircraft currently tracked as military over this country, written by "
    "the aviation sampler. This compares a count taken now with a mean of counts taken now, "
    "so it does not describe the report's period; ADS-B coverage is uneven and incomplete, "
    "and a count is not a claim about what those aircraft were doing."
)
PARTIAL_BASELINE = (
    "This is the only baseline the application records that fits this scope. There is no "
    "recorded baseline for the drawn outline, for shipping, for thermal detections, for "
    "interference or for reporting volume, so nothing here says whether those were normal."
)


def _placements(items: Sequence[EvidenceItem]) -> tuple[EvidencePlacement, ...]:
    return tuple(
        EvidencePlacement(item.label, item.lon, item.lat, item.geo_confidence or "none")
        for item in items
    )


def _scope_text(job: Job, query: ResearchQuery | None) -> str:
    return trigger_text(
        job.request.question,
        job.title,
        " ".join(query.terms) if query is not None else " ".join(job.terms),
    )


def _cameras_wanted(job: Job, query: ResearchQuery | None) -> bool:
    """The reviewed trigger table governs camera coverage exactly as it governs registers."""
    if job.request.effective_area is not None:
        return True
    text = _scope_text(job, query)
    return AssetClass.CAMERAS.value in {row.name for row in asset_triggers(text)}


class AreaContextService:
    def __init__(
        self,
        geography: AreaGeography,
        baselines: BaselineRepository | None = None,
        interference: InterferenceCells | None = None,
    ) -> None:
        self._geography, self._baselines = geography, baselines
        self._interference = interference

    def _countries(self, job: Job, query: ResearchQuery | None) -> tuple[str, ...]:
        chosen = job.request.country_isos or (query.country_isos if query else ()) or job.countries
        return tuple(dict.fromkeys(value.upper() for value in chosen))

    async def build(
        self,
        job: Job,
        query: ResearchQuery | None,
        items: Sequence[EvidenceItem],
        store: EventStore,
    ) -> AreaContext | None:
        countries = self._countries(job, query)
        box = (
            (job.bbox.west, job.bbox.south, job.bbox.east, job.bbox.north)
            if job.bbox is not None
            else None
        )
        result = self._geography.assemble(
            area=job.request.effective_area,
            country_isos=countries,
            box=box,
            box_label=job.request.conflict_id,
            placements=_placements(items),
            cameras=_cameras_wanted(job, query),
        )
        if result is None:
            return None
        baselines = await self._baseline_rows(job, countries, store)
        wanted = eligible_instruments(
            _scope_text(job, query), drawn=job.request.effective_area is not None
        )
        readings = (
            sweep_instruments(
                self._geography,
                wanted,
                ScopeRequest(job.request.effective_area, countries, box, job.request.conflict_id),
                store,
                job.now,
                self._interference,
            )
            if wanted
            else ()
        )
        return AreaContext(
            result.scope,
            result.containment,
            result.breakdown,
            baselines,
            PARTIAL_BASELINE if baselines else NO_BASELINE,
            result.registers,
            readings,
            NO_INSTRUMENTS,
        )

    async def _baseline_rows(
        self, job: Job, countries: tuple[str, ...], store: EventStore
    ) -> tuple[BaselineComparison, ...]:
        """Only recorded aggregates. A drawn outline has no baseline and never gets one."""
        if self._baselines is None or not countries:
            return ()
        means = await self._baselines.means(BASELINE_KIND, job.now - timedelta(days=BASELINE_DAYS))
        if not means:
            return ()
        events = store.query(
            EventQuery(categories=frozenset({Category.AVIATION}), limit=AVIATION_POOL)
        )
        observed = military_by_country(events)
        rows = [
            BaselineComparison(
                BASELINE_KIND,
                iso,
                f"Military aircraft tracked over {iso}",
                observed.get(iso, 0),
                means[iso],
                BASELINE_DAYS,
                MILITARY_BASIS,
            )
            for iso in countries[:MAX_BASELINE_COUNTRIES]
            if iso in means
        ]
        return tuple(rows)


async def attach_area_context(
    service: AreaContextService | None,
    job: Job,
    query: ResearchQuery | None,
    selection: Selection,
    receipt: ResearchReceipt | None,
    store: EventStore,
    unchanged: Selection | None = None,
) -> ResearchReceipt | None:
    """No service, no receipt, no resolvable geography or no change leaves the receipt alone."""
    if service is None or receipt is None or selection is unchanged:
        return receipt
    context = await service.build(job, query, selection.items, store)
    return receipt if context is None else replace(receipt, area_context=context)
