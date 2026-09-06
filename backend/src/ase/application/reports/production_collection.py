"""Prepare the private collection pool and its initial coverage receipt."""

from collections.abc import Callable

from ase.application.ports.feeds import EventStore
from ase.application.ports.research import ResearchCollection
from ase.application.reports.production_types import Job, Totals
from ase.application.reports.progress import Progress, reached
from ase.application.reports.research import collect_report_evidence
from ase.domain.direction import Direction
from ase.domain.research import ResearchQuery
from ase.domain.research_records import ResearchReceipt
from ase.domain.research_runs import ResearchStage
from ase.domain.validation import Finding, Severity


async def prepare_collection(
    job: Job,
    direction: Direction | None,
    totals: Totals,
    collection: ResearchCollection | None,
    store_factory: Callable[[], EventStore] | None,
    live_store: EventStore,
    progress: Progress | None,
) -> tuple[EventStore, ResearchReceipt | None, ResearchQuery | None]:
    store = live_store
    receipt: ResearchReceipt | None = None
    query: ResearchQuery | None = None
    if job.request.research_mode is not None:
        query = ResearchQuery(
            question=job.request.question or job.title,
            since=job.now - job.window,
            until=job.now,
            languages=job.request.research_languages,
            terms=tuple(direction.search_terms if direction else job.terms),
            mode=job.request.research_mode,
            focus=job.request.research_focus,
            country_iso=job.request.country_iso,
            subject=job.request.research_subject,
        )
        if not query.terms:
            totals.findings.append(
                Finding(
                    "research_query_plan",
                    Severity.WARNING,
                    "research",
                    "No planned search terms are available. "
                    "Targeted query planning is missing; "
                    "collection receipts identify the sources actually attempted.",
                )
            )
        await reached(progress, ResearchStage.COLLECTING)
        store, receipt = await collect_report_evidence(
            query,
            job.request,
            collection,
            store_factory,
            live_store,
            seed_events=job.seed_events,
            seed_attempts=job.seed_attempts,
        )
    return store, receipt, query
