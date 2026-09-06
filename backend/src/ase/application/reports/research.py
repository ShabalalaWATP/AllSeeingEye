"""Collect a private, bounded evidence pool before report drafting."""

from collections.abc import Callable

from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.ports.research import ResearchCollection
from ase.application.reports.request import ReportRequest
from ase.domain.errors import InvalidRequest
from ase.domain.events import Event
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
) -> tuple[EventStore, ResearchReceipt]:
    if store_factory is None:
        raise InvalidRequest("On-demand research collection is unavailable")
    private_focus = query.focus in {ResearchFocus.DOCUMENT, ResearchFocus.MEDIA}
    if private_focus:
        # Extracted private text must not become an unsolicited public search query.
        batch = ResearchBatch()
    elif collection is None:
        raise InvalidRequest("On-demand research collection is unavailable")
    else:
        batch = await collection.collect(query)
    private = store_factory()
    if not private_focus:
        # Copy public context only for public research. Unrelated high-ranked live items
        # must not crowd supplied document/media passages out of their own report.
        retained = live_store.query(
            EventQuery(
                since=query.since,
                country_iso=request.country_iso,
                categories=frozenset(request.categories),
                limit=1000,
            )
        )
        private.upsert(item for item in retained if item.published_at < query.until)
    private.upsert(batch.items)
    private.upsert(seed_events)
    return private, ResearchReceipt.build(
        query, (*seed_attempts, *batch.attempts), len(batch.items)
    )
