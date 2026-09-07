"""Collect a private, bounded evidence pool before report drafting."""

from collections.abc import Callable

from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.ports.research import ReplanCallback, ResearchCollection
from ase.application.reports.request import ReportRequest
from ase.domain.errors import InvalidRequest
from ase.domain.events import Event
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import CollectionAttempt, ResearchBatch, ResearchFocus, ResearchQuery
from ase.domain.research_records import ResearchReceipt


async def collect_report_evidence(
    query: ResearchQuery,
    request: ReportRequest,
    collection: ResearchCollection | None,
    store_factory: Callable[[], EventStore] | None,
    live_store: EventStore,
    seed_events: tuple[Event, ...] = (),
    seed_attempts: tuple[CollectionAttempt, ...] = (),
    replan: ReplanCallback | None = None,
) -> tuple[EventStore, ResearchReceipt]:
    if store_factory is None:
        raise InvalidRequest("On-demand research collection is unavailable")
    private_focus = query.focus in {ResearchFocus.DOCUMENT, ResearchFocus.MEDIA}
    if len(seed_attempts) > 64:
        raise InvalidRequest("Too many retained collection receipts")
    if seed_attempts and not private_focus and collection is not None:
        planned = collection.plan(query)
        if sum(task.selected for task in planned.tasks) + len(seed_attempts) > 64:
            raise InvalidRequest("Expanded plan and retained receipts exceed the 64-task limit")
    if private_focus:
        # Extracted private text must not become an unsolicited public search query.
        batch = ResearchBatch()
    elif collection is None:
        raise InvalidRequest("On-demand research collection is unavailable")
    else:
        batch = (
            await collection.collect(query, replan=replan)
            if replan
            else await collection.collect(query)
        )
    private = store_factory()
    if (
        not private_focus
        and query.area is None
        and query.effective_time_basis is not EvidenceTimeBasis.RECORDED
    ):
        # Copy public context only for public research. Unrelated high-ranked live items
        # must not crowd supplied document/media or historical project records out.
        retained = live_store.query(
            EventQuery(
                since=query.since,
                country_iso=request.country_iso,
                categories=frozenset(request.categories),
                limit=1000,
            )
        )
        private.upsert(
            item
            for item in retained
            if item.published_at is not None and item.published_at < query.until
        )
    private.upsert(batch.items)
    private.upsert(seed_events)
    return private, ResearchReceipt.build(
        query, (*seed_attempts, *batch.attempts), len(batch.items), batch.plan, batch.passes
    )
