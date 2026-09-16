"""What the report actually read, and what it did not, in counts the reader can check.

Coverage receipts already record every source considered, attempted and unavailable,
and selection records what was folded or left outside the evidence limit. This states
those limits on the report itself instead of leaving them implied. Every number comes
from a recorded receipt: nothing here is estimated.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

COVERAGE_VERSION = "ase-evidence-coverage-v1"
RERANK_APPLIED = "applied"
RERANK_NOT_ATTEMPTED = "not_attempted"


@dataclass(frozen=True, slots=True)
class EvidenceCoverage:
    """Counts of sources and items at each retrieval stage, for one report version."""

    sources_considered: int = 0
    sources_read: int = 0
    sources_empty: int = 0
    sources_unavailable: int = 0
    sources_not_attempted: int = 0
    items_retrieved: int = 0
    items_considered: int = 0
    items_selected: int = 0
    duplicates_merged: int = 0
    items_flagged: int = 0
    reranked_candidates: int = 0
    rerank_status: str = RERANK_NOT_ATTEMPTED
    method_version: str = COVERAGE_VERSION

    def describe(self) -> str:
        rerank = (
            f"{self.reranked_candidates} item(s) ranked by embedding similarity"
            if self.rerank_status == RERANK_APPLIED
            else f"similarity ranking not applied ({self.rerank_status})"
        )
        return (
            f"Coverage: {self.sources_considered} source(s) considered, "
            f"{self.sources_read} read, {self.sources_empty} returned nothing, "
            f"{self.sources_unavailable} unavailable, "
            f"{self.sources_not_attempted} not attempted within the plan's limits; "
            f"{self.items_retrieved} item(s) retrieved, {self.items_considered} eligible, "
            f"{self.duplicates_merged} duplicate item(s) merged, "
            f"{self.items_flagged} withheld for instruction-like text, "
            f"{self.items_selected} placed before the model; {rerank}. "
            "Sources not read may hold relevant reporting; absence here is not absence."
        )


def coverage_to_dict(coverage: EvidenceCoverage | None) -> dict[str, Any] | None:
    if coverage is None:
        return None
    return {
        "sources_considered": coverage.sources_considered,
        "sources_read": coverage.sources_read,
        "sources_empty": coverage.sources_empty,
        "sources_unavailable": coverage.sources_unavailable,
        "sources_not_attempted": coverage.sources_not_attempted,
        "items_retrieved": coverage.items_retrieved,
        "items_considered": coverage.items_considered,
        "items_selected": coverage.items_selected,
        "duplicates_merged": coverage.duplicates_merged,
        "items_flagged": coverage.items_flagged,
        "reranked_candidates": coverage.reranked_candidates,
        "rerank_status": coverage.rerank_status,
        "method_version": coverage.method_version,
    }


def coverage_from_dict(data: Mapping[str, Any] | None) -> EvidenceCoverage | None:
    """Unknown or legacy payloads stay absent rather than inventing zero coverage."""
    if not isinstance(data, Mapping) or data.get("method_version") != COVERAGE_VERSION:
        return None

    def count(name: str) -> int:
        return max(0, int(data.get(name, 0) or 0))

    status = data.get("rerank_status", RERANK_NOT_ATTEMPTED)
    return EvidenceCoverage(
        sources_considered=count("sources_considered"),
        sources_read=count("sources_read"),
        sources_empty=count("sources_empty"),
        sources_unavailable=count("sources_unavailable"),
        sources_not_attempted=count("sources_not_attempted"),
        items_retrieved=count("items_retrieved"),
        items_considered=count("items_considered"),
        items_selected=count("items_selected"),
        duplicates_merged=count("duplicates_merged"),
        items_flagged=count("items_flagged"),
        reranked_candidates=count("reranked_candidates"),
        rerank_status=str(status)[:120] if isinstance(status, str) else RERANK_NOT_ATTEMPTED,
    )


def source_counts(statuses: Sequence[str], planned: int) -> tuple[int, int, int, int, int]:
    """Read, empty, unavailable, not attempted and considered, from recorded attempts."""
    read = sum(1 for status in statuses if status == "read")
    empty = sum(1 for status in statuses if status == "empty")
    unavailable = len(statuses) - read - empty
    considered = max(planned, len(statuses))
    return read, empty, unavailable, max(0, considered - len(statuses)), considered
