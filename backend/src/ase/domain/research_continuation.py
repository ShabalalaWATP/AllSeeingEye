"""Bounded model continuation receipts, not verified analytical conclusions."""

from dataclasses import dataclass
from typing import Any, Literal

Decision = Literal["continue", "replan", "sufficient"]
Basis = Literal[
    "empty_results",
    "potential_conflict",
    "question_addressed",
    "insufficient_context",
    "invalid_or_unavailable",
]


def bounded_text(value: str, limit: int, *, empty: bool = False) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= limit
        and (empty or bool(value.strip()))
        and not any(ord(c) < 32 or ord(c) == 127 for c in value)
    )


@dataclass(frozen=True, slots=True)
class EvidenceExcerpt:
    event_id: str
    source_id: str
    content_hash: str
    field: Literal["title", "summary"]
    quote: str

    def __post_init__(self) -> None:
        if not all(
            bounded_text(v, n)
            for v, n in (
                (self.event_id, 128),
                (self.source_id, 120),
                (self.content_hash, 128),
                (self.quote, 500),
            )
        ) or self.field not in {"title", "summary"}:
            raise ValueError("Invalid continuation citation")


@dataclass(frozen=True, slots=True)
class ContinuationTrace:
    decision: Decision
    requested_decision: Decision | None
    basis: Basis
    rationale: str
    citations: tuple[EvidenceExcerpt, ...]
    gaps: tuple[str, ...]
    model: str
    context_count: int
    total_count: int
    override_reason: str | None = None
    policy_version: str = "ase-collection-review-v1"

    def __post_init__(self) -> None:
        if self.policy_version != "ase-collection-review-v1":
            raise ValueError("Invalid continuation policy")
        choices = {"continue", "replan", "sufficient"}
        if (
            self.decision not in choices
            or self.requested_decision not in choices | {None}
            or self.basis
            not in {
                "empty_results",
                "potential_conflict",
                "question_addressed",
                "insufficient_context",
                "invalid_or_unavailable",
            }
        ):
            raise ValueError("Invalid continuation decision")
        if (
            not bounded_text(self.rationale, 1000)
            or not bounded_text(self.model, 200, empty=True)
            or (self.override_reason is not None and not bounded_text(self.override_reason, 1000))
        ):
            raise ValueError("Invalid continuation explanation")
        if (
            not isinstance(self.citations, tuple)
            or len(self.citations) > 8
            or any(not isinstance(row, EvidenceExcerpt) for row in self.citations)
            or len(set(self.citations)) != len(self.citations)
        ):
            raise ValueError("Invalid continuation citations")
        if (
            not isinstance(self.gaps, tuple)
            or len(self.gaps) > 8
            or any(not bounded_text(row, 300) for row in self.gaps)
        ):
            raise ValueError("Invalid continuation gaps")
        if (
            type(self.context_count) is not int
            or type(self.total_count) is not int
            or not 0 <= self.context_count <= min(20, self.total_count)
            or self.total_count > 1000
        ):
            raise ValueError("Invalid continuation context counts")


def continuation_from_dict(data: Any) -> ContinuationTrace | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("Invalid continuation receipt")
    return ContinuationTrace(
        **{
            **data,
            "citations": tuple(EvidenceExcerpt(**row) for row in data["citations"]),
            "gaps": tuple(data["gaps"]),
        }
    )
