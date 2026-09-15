"""A failed second pass cannot hide a first-pass search whose items stay admitted."""

import pytest

from ase.application.research.replanning import _merge
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchBatch
from test_research_collection import QUERY, event


def _attempt(status: CollectionStatus, count: int = 0) -> CollectionAttempt:
    return CollectionAttempt("fake_feed", "Fake feed", status, count)


@pytest.mark.parametrize(
    "second_status",
    [CollectionStatus.FAILED, CollectionStatus.EMPTY, CollectionStatus.TIMED_OUT],
)
def test_completed_first_pass_receipt_survives_non_completed_second_pass(
    second_status: CollectionStatus,
) -> None:
    first = ResearchBatch(
        items=(event("kept"),), attempts=(_attempt(CollectionStatus.COMPLETED, 1),)
    )
    second = ResearchBatch(attempts=(_attempt(second_status),))
    merged = _merge(first, QUERY, False, second, QUERY)
    assert [row.id for row in merged.items] == ["kept"]
    assert merged.attempts[0].status is CollectionStatus.COMPLETED
    assert merged.attempts[0].result_count == 1
    assert merged.passes[1].attempts[0].status is second_status


def test_completed_second_pass_still_replaces_the_first_receipt() -> None:
    first = ResearchBatch(attempts=(_attempt(CollectionStatus.COMPLETED, 1),))
    second = ResearchBatch(attempts=(_attempt(CollectionStatus.COMPLETED, 3),))
    merged = _merge(first, QUERY, False, second, QUERY)
    assert merged.attempts[0].result_count == 3


def test_failed_second_pass_still_replaces_an_empty_first_search() -> None:
    first = ResearchBatch(attempts=(_attempt(CollectionStatus.EMPTY),))
    second = ResearchBatch(attempts=(_attempt(CollectionStatus.FAILED),))
    merged = _merge(first, QUERY, False, second, QUERY)
    assert merged.attempts[0].status is CollectionStatus.FAILED
