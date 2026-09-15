"""Final evidence selection follows the authorised research search, not stale direction."""

from dataclasses import replace
from datetime import timedelta
from typing import Any

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.reports.production_checkpoint import (
    ProductionSnapshot,
    collection_from_dict,
    collection_to_dict,
)
from ase.application.reports.production_collection import prepare_collection
from ase.application.reports.production_selection import select_for_job
from ase.application.reports.production_types import Totals
from ase.application.reports.request import ReportRequest
from ase.application.reports.research import collect_report_evidence_with_query
from ase.application.research.replanning import collect_with_replan
from ase.domain.direction import Direction
from ase.domain.research import (
    ResearchBatch,
    ResearchMode,
    ResearchQuery,
)
from ase.domain.research_plan import QueryVariant
from feeds_helpers import NOW, make_event
from report_job_snapshot_helpers import fixture_job


@pytest.mark.parametrize("stale_direction", [False, True])
def test_operator_term_survives_crowded_basic_selection(stale_direction: bool) -> None:
    request = ReportRequest(
        "ask",
        question="What is known about zirconium?",
        research_mode=ResearchMode.QUICK,
        research_terms=("zirconium",),
    )
    job = replace(fixture_job(request), terms=("stale",))
    direction = Direction("Old question", search_terms=("stale",)) if stale_direction else None
    store = InMemoryEventStore()
    store.upsert(
        (
            *(
                make_event(
                    f"distractor-{index}",
                    source_id=f"distractor-{index}",
                    title=f"Stale item {index}",
                )
                for index in range(30)
            ),
            make_event(
                "direct",
                source_id="direct",
                title="Zirconium answer",
                published_at=NOW - timedelta(hours=12),
            ),
        )
    )
    query = ResearchQuery(
        request.question or "",
        job.period_from,
        job.period_to,
        terms=request.research_terms or (),
    )

    selected = select_for_job(store, {}, job, direction, runtime_query=query)

    assert selected.considered == 31
    assert len(selected.items) == 24
    assert any(item.title == "Zirconium answer" for item in selected.items)


async def test_collection_uses_operator_override_and_retains_variant() -> None:
    variant = QueryVariant("fr", ("zirconium français",), original_terms=("zirconium",))
    request = ReportRequest(
        "ask",
        question="What is known about zirconium?",
        research_mode=ResearchMode.QUICK,
        research_terms=("zirconium",),
        research_languages=("en", "fr"),
        research_query_variants=(variant,),
        country_iso="GB",
    )
    job = replace(fixture_job(request), terms=("stale",))

    class Collection:
        received: ResearchQuery | None = None

        async def collect(self, query: ResearchQuery, **_: Any) -> ResearchBatch:
            self.received = query
            return ResearchBatch()

    collection = Collection()
    _, receipt, effective = await prepare_collection(
        job,
        Direction("Old", search_terms=("stale",)),
        Totals(),
        collection,  # type: ignore[arg-type]
        InMemoryEventStore,
        InMemoryEventStore(),
        None,
    )
    assert collection.received == effective
    assert effective and effective.terms == ("zirconium",)
    assert effective.query_variants == (variant,)
    assert effective.country_isos == ("GB",)
    assert receipt and receipt.terms == effective.terms


class _RevisionProvider:
    id = "revision-source"
    name = "Revision source"
    language = "fr"

    def __init__(self) -> None:
        self.queries: list[ResearchQuery] = []

    def supports(self, query: ResearchQuery) -> bool:
        return True

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        self.queries.append(query)
        return ResearchBatch(
            items=(
                make_event(
                    "revised",
                    source_id=self.id,
                    title="zirconium révisé",
                    published_at=NOW - timedelta(hours=1),
                ),
            )
            if query.terms == ("zirconium révisé",)
            else ()
        )


async def test_accepted_revision_and_variant_are_frozen_for_selection_and_resume() -> None:
    request = ReportRequest(
        "ask",
        question="What is known about zirconium?",
        research_mode=ResearchMode.QUICK,
        research_terms=("zirconium",),
        research_languages=("en", "fr"),
    )
    job = fixture_job(request)
    query = ResearchQuery(
        request.question or "",
        job.period_from,
        job.period_to,
        languages=request.research_languages,
        terms=request.research_terms or (),
        time_basis=request.effective_time_basis,
    )
    provider = _RevisionProvider()
    variant = QueryVariant("fr", ("zirconium révisé",), original_terms=("zirconium revised",))

    async def revise(original: ResearchQuery, *_: Any) -> ResearchQuery:
        return replace(
            original,
            terms=("zirconium revised",),
            query_variants=(variant,),
        )

    batch = await collect_with_replan((provider,), query, revise)
    assert batch.effective_query == replace(
        query, terms=("zirconium revised",), query_variants=(variant,)
    )
    assert batch.plan and batch.plan.replans == 1
    assert batch.plan.tasks[0].query_variant == variant
    assert batch.passes[0].terms == ("zirconium",)
    assert batch.passes[1].terms == ("zirconium revised",)

    class Collection:
        async def collect(self, received: ResearchQuery, **_: Any) -> ResearchBatch:
            assert received == query
            return batch

    store, receipt, effective = await collect_report_evidence_with_query(
        query,
        request,
        Collection(),  # type: ignore[arg-type]
        InMemoryEventStore,
        InMemoryEventStore(),
    )
    assert effective == batch.effective_query
    assert receipt.terms == ("zirconium revised",)
    assert receipt.plan and receipt.plan.tasks[0].query_variant == variant
    selected = select_for_job(
        store,
        {},
        job,
        Direction("Old", search_terms=("stale",)),
        runtime_query=effective,
        receipt=receipt,
    )
    assert [item.title for item in selected.items] == ["zirconium révisé"]
    restored = collection_from_dict(
        collection_to_dict(ProductionSnapshot(selected, None, receipt, effective, Totals()))
    )
    assert restored.query == effective
    assert restored.receipt == receipt
    assert restored.query and restored.query.query_variants == (variant,)
    _, prepared_receipt, prepared_query = await prepare_collection(
        job,
        Direction("Old", search_terms=("stale",)),
        Totals(),
        Collection(),  # type: ignore[arg-type]
        InMemoryEventStore,
        InMemoryEventStore(),
        None,
    )
    assert prepared_query == effective
    assert prepared_receipt and prepared_receipt.plan
    assert prepared_receipt.plan.tasks[0].provenance == "model_replanned_variant"
    assert prepared_receipt.passes[0].plan
    assert prepared_receipt.passes[0].plan.tasks[0].provenance == "original_terms"


async def test_rejected_scope_revision_is_absent_from_effective_query_and_receipt() -> None:
    job = fixture_job(
        ReportRequest(
            "ask",
            question="Zirconium",
            research_mode=ResearchMode.QUICK,
            research_terms=("zirconium",),
        )
    )
    query = ResearchQuery("Zirconium", job.period_from, job.period_to, terms=("zirconium",))
    provider = _RevisionProvider()

    async def unsafe(original: ResearchQuery, *_: Any) -> ResearchQuery:
        return replace(original, terms=("forbidden",), country_iso="US")

    batch = await collect_with_replan((provider,), query, unsafe)
    assert batch.effective_query == query
    assert batch.plan and batch.plan.replans == 0
    assert all(received.country_iso is None for received in provider.queries)
    assert all("forbidden" not in passed.terms for passed in batch.passes)
