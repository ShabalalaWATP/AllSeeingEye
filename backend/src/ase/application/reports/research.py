"""Collect a private, bounded evidence pool before report drafting."""

from collections.abc import Callable
from dataclasses import replace

from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.ports.research import (
    CheckpointedResearchCollection,
    RankedResearchCollection,
    ReplanCallback,
    ResearchCollection,
    SourceOperationCheckpoints,
)
from ase.application.reports.request import ReportRequest
from ase.domain.country_subjects import annotate_fresh_country_subject
from ase.domain.errors import InvalidRequest
from ase.domain.events import Event
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import CollectionAttempt, ResearchBatch, ResearchFocus, ResearchQuery
from ase.domain.research_capacity import MAX_COLLECTION_RECEIPTS, MAX_SEED_RECEIPTS
from ase.domain.research_records import ResearchReceipt


async def _collect_batch(
    query: ResearchQuery,
    request: ReportRequest,
    collection: ResearchCollection | None,
    replan: ReplanCallback | None,
    source_operations: SourceOperationCheckpoints | None,
) -> ResearchBatch:
    if query.focus in {ResearchFocus.DOCUMENT, ResearchFocus.MEDIA}:
        return ResearchBatch()
    if collection is None:
        raise InvalidRequest("On-demand research collection is unavailable")
    if source_operations is not None:
        if not isinstance(collection, CheckpointedResearchCollection):
            raise InvalidRequest("Checkpointed source acquisition is unavailable")
        return await collection.collect_checkpointed(
            query, request.canonical_requirements, source_operations, replan=replan
        )
    if request.canonical_requirements and isinstance(collection, RankedResearchCollection):
        return await collection.collect_with_requirements(
            query, request.canonical_requirements, replan=replan
        )
    if replan:
        return await collection.collect(query, replan=replan)
    return await collection.collect(query)


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
    store, receipt, _ = await collect_report_evidence_with_query(
        query,
        request,
        collection,
        store_factory,
        live_store,
        seed_events,
        seed_attempts,
        replan,
    )
    return store, receipt


async def collect_report_evidence_with_query(
    query: ResearchQuery,
    request: ReportRequest,
    collection: ResearchCollection | None,
    store_factory: Callable[[], EventStore] | None,
    live_store: EventStore,
    seed_events: tuple[Event, ...] = (),
    seed_attempts: tuple[CollectionAttempt, ...] = (),
    replan: ReplanCallback | None = None,
    source_operations: SourceOperationCheckpoints | None = None,
) -> tuple[EventStore, ResearchReceipt, ResearchQuery]:
    if store_factory is None:
        raise InvalidRequest("On-demand research collection is unavailable")
    private_focus = query.focus in {ResearchFocus.DOCUMENT, ResearchFocus.MEDIA}
    if len(seed_attempts) > MAX_SEED_RECEIPTS:
        raise InvalidRequest("Too many retained collection receipts")
    if seed_attempts and not private_focus and collection is not None:
        planned = collection.plan(query)
        if (
            sum(task.selected for task in planned.tasks) + len(seed_attempts)
            > MAX_COLLECTION_RECEIPTS
        ):
            raise InvalidRequest(
                "Expanded plan and retained receipts exceed the "
                f"{MAX_COLLECTION_RECEIPTS}-receipt limit"
            )
    # Extracted private text must not become an unsolicited public search query.
    batch = await _collect_batch(query, request, collection, replan, source_operations)
    effective_query = batch.effective_query or query
    if effective_query != query and (
        batch.plan is None
        or batch.plan.replans != 1
        or replace(effective_query, terms=query.terms, query_variants=query.query_variants) != query
    ):
        raise InvalidRequest("Collection returned an unauthorised search revision")
    private = store_factory()
    if (
        not private_focus
        and query.area is None
        and query.effective_time_basis is not EvidenceTimeBasis.RECORDED
    ):
        # Copy public context only for public research. Unrelated high-ranked live items
        # must not crowd supplied document/media or historical project records out.
        countries: tuple[str | None, ...] = query.country_isos or (None,)
        retained: dict[str, Event] = {}
        for country in countries:
            for item in live_store.query(
                EventQuery(
                    since=query.since,
                    until=query.until,
                    country_iso=country,
                    time_basis=query.effective_time_basis,
                    categories=frozenset(request.categories),
                    limit=1000 // len(countries),
                )
            ):
                retained.setdefault(item.id, item)
        private.upsert(tuple(retained.values())[:1000])
    private.upsert(
        annotate_fresh_country_subject(item, query.country_isos)
        if query.focus is ResearchFocus.GENERAL
        and query.area is None
        and query.effective_time_basis is not EvidenceTimeBasis.RECORDED
        and query.country_isos
        else item
        for item in batch.items
    )
    private.upsert(seed_events)
    return (
        private,
        ResearchReceipt.build(
            effective_query,
            (*seed_attempts, *batch.attempts),
            len(batch.items),
            batch.plan,
            batch.passes,
        ),
        effective_query,
    )
