"""The report states what was considered, read, merged and left unread."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

from ase.application.reports.coverage_summary import coverage_for
from ase.application.reports.evidence_rerank import NO_PROFILE
from ase.application.reports.selection import Selection
from ase.domain.evidence_coverage import (
    RERANK_APPLIED,
    RERANK_NOT_ATTEMPTED,
    coverage_from_dict,
    coverage_to_dict,
)
from ase.domain.report_records import quality_from_dict, quality_to_dict
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchMode,
    ResearchQuery,
)
from ase.domain.research_plan import ResearchPlan, ResearchTask
from ase.domain.research_records import ResearchReceipt
from report_documents_helpers import document_records

NOW = datetime(2026, 9, 5, tzinfo=UTC)
EARLIER = NOW - timedelta(days=7)


def attempt(source_id: str, status: CollectionStatus, count: int = 0) -> CollectionAttempt:
    return CollectionAttempt(
        source_id=source_id,
        source_name=source_id.title(),
        status=status,
        result_count=count,
        explanation="fixture",
        language="en",
    )


def plan(source_ids: tuple[str, ...]) -> ResearchPlan:
    return ResearchPlan(
        question="What changed?",
        since=EARLIER,
        until=NOW,
        languages=("en",),
        tasks=tuple(
            ResearchTask(source_id, source_id.title(), True, True, "en", ("grid",), "fixture")
            for source_id in source_ids
        ),
        request_limit=6,
        seconds_limit=60.0,
        item_limit=100,
        mode=ResearchMode.DETAILED.value,
    )


def receipt(*, planned: tuple[str, ...], attempts: tuple[CollectionAttempt, ...], items: int):
    query = ResearchQuery(
        "What changed?", EARLIER, NOW, terms=("grid",), mode=ResearchMode.DETAILED
    )
    return ResearchReceipt.build(query, attempts, items, plan(planned))


def selection(**changes) -> Selection:
    _, version = document_records()
    base = Selection(version.evidence, flagged=2, considered=90, merged=47, reranked=60)
    return replace(base, **changes)


def test_coverage_counts_sources_read_empty_unavailable_and_unplanned():
    rows = receipt(
        planned=tuple(f"s{index}" for index in range(1, 39)),
        attempts=(
            *(attempt(f"s{index}", CollectionStatus.COMPLETED, 4) for index in range(1, 13)),
            *(attempt(f"s{index}", CollectionStatus.UNAVAILABLE) for index in range(13, 16)),
            attempt("s16", CollectionStatus.EMPTY),
        ),
        items=120,
    )
    coverage = coverage_for(selection(), rows)
    assert coverage.sources_considered == 38
    assert coverage.sources_read == 12
    assert coverage.sources_unavailable == 3
    assert coverage.sources_empty == 1
    assert coverage.sources_not_attempted == 22
    assert coverage.items_retrieved == 120
    assert coverage.duplicates_merged == 47


def test_a_source_attempted_twice_is_counted_once_at_its_best_outcome():
    rows = receipt(
        planned=("alpha",),
        attempts=(
            attempt("alpha", CollectionStatus.TIMED_OUT),
            attempt("alpha", CollectionStatus.COMPLETED, 3),
        ),
        items=3,
    )
    coverage = coverage_for(selection(), rows)
    assert coverage.sources_considered == 1
    assert coverage.sources_read == 1 and coverage.sources_unavailable == 0


def test_a_completed_attempt_with_no_items_counts_as_empty_not_read():
    rows = receipt(
        planned=("alpha",), attempts=(attempt("alpha", CollectionStatus.COMPLETED),), items=0
    )
    coverage = coverage_for(selection(), rows)
    assert coverage.sources_read == 0 and coverage.sources_empty == 1


def test_coverage_without_a_research_receipt_reports_only_the_item_counts():
    coverage = coverage_for(selection(), None)
    assert coverage.sources_considered == 0 and coverage.items_retrieved == 0
    assert coverage.items_considered == 90 and coverage.items_flagged == 2


def test_the_rerank_status_reports_what_actually_happened():
    assert coverage_for(selection(), None).rerank_status == RERANK_APPLIED
    assert coverage_for(selection(reranked=0), None).rerank_status == RERANK_NOT_ATTEMPTED
    fallback = coverage_for(selection(reranked=0, rerank_reason=NO_PROFILE), None)
    assert fallback.rerank_status == NO_PROFILE
    assert "similarity ranking not applied (no_embeddings_profile)" in fallback.describe()


def test_the_summary_reads_as_plain_counts_with_an_honest_caveat():
    rows = receipt(
        planned=tuple(f"s{index}" for index in range(1, 39)),
        attempts=(
            *(attempt(f"s{index}", CollectionStatus.COMPLETED, 4) for index in range(1, 13)),
            *(attempt(f"s{index}", CollectionStatus.UNAVAILABLE) for index in range(13, 16)),
        ),
        items=120,
    )
    text = coverage_for(selection(), rows).describe()
    assert "38 source(s) considered, 12 read" in text
    assert "3 unavailable" in text
    assert "47 duplicate item(s) merged" in text
    assert "absence here is not absence" in text


def test_coverage_survives_the_quality_round_trip_and_stays_absent_when_legacy():
    _, version = document_records()
    coverage = coverage_for(selection(), None)
    quality = replace(version.quality, coverage=coverage)
    restored = quality_from_dict(quality_to_dict(quality))
    assert restored.coverage == coverage
    assert quality_from_dict(quality_to_dict(version.quality)).coverage is None
    assert "coverage" not in quality_to_dict(version.quality)
    assert coverage_from_dict(None) is None
    assert coverage_from_dict({"method_version": "other"}) is None
    assert coverage_from_dict(coverage_to_dict(coverage)) == coverage


def test_the_quality_description_carries_the_coverage_only_when_it_exists():
    _, version = document_records()
    assert "Coverage:" not in version.quality.describe()
    with_coverage = replace(version.quality, coverage=coverage_for(selection(), None))
    assert "Coverage:" in with_coverage.describe()
