"""Operator hypotheses are search context, never verified entity matches."""

import re
from dataclasses import dataclass
from typing import Literal

TaskPurpose = Literal["baseline", "challenge", "disambiguation"]


def _id(value: str) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value) is not None


def _terms(values: tuple[str, ...], maximum: int) -> None:
    if (
        not isinstance(values, tuple)
        or len(values) > maximum
        or any(
            not isinstance(v, str)
            or not v.strip()
            or len(v) > 300
            or any(ord(c) < 32 or ord(c) == 127 for c in v)
            for v in values
        )
        or sum(map(len, values)) > 1000
    ):
        raise ValueError("Provide bounded text without control characters")


@dataclass(frozen=True, slots=True)
class ResearchCandidate:
    id: str
    label: str
    identifiers: tuple[str, ...] = ()
    origin: Literal["operator", "model"] = "operator"

    def __post_init__(self) -> None:
        if self.origin not in {"operator", "model"}:
            raise ValueError("Invalid research task origin")
        if (
            not _id(self.id)
            or not isinstance(self.label, str)
            or not self.label.strip()
            or not 1 <= len(self.label) <= 200
        ):
            raise ValueError("Invalid candidate hypothesis identity")
        _terms((self.label,), 1)
        _terms(self.identifiers, 8)


@dataclass(frozen=True, slots=True)
class PlannedQueryTask:
    id: str
    source_id: str
    purpose: Literal["challenge", "disambiguation"]
    terms: tuple[str, ...]
    candidate_id: str | None = None
    origin: Literal["operator", "model"] = "operator"

    def __post_init__(self) -> None:
        if self.origin not in {"operator", "model"}:
            raise ValueError("Invalid research task origin")
        if (
            not _id(self.id)
            or not isinstance(self.source_id, str)
            or not 1 <= len(self.source_id) <= 120
        ):
            raise ValueError("Invalid planned task identity")
        _terms((self.source_id,), 1)
        if self.purpose not in {"challenge", "disambiguation"}:
            raise ValueError("Invalid operator task purpose")
        if self.candidate_id is not None and not _id(self.candidate_id):
            raise ValueError("Invalid candidate reference")
        if self.purpose == "disambiguation" and self.candidate_id is None:
            raise ValueError("Disambiguation requires a candidate hypothesis")
        _terms(self.terms, 12)
        if not self.terms:
            raise ValueError("Planned tasks require explicit search terms")


def validate_operator_plan(
    candidates: tuple[ResearchCandidate, ...],
    tasks: tuple[PlannedQueryTask, ...],
    source_ids: tuple[str, ...] | None,
    *,
    public_scope: bool = True,
) -> None:
    if (candidates or tasks) and not public_scope:
        raise ValueError("Operator source tasks require public-source research")
    for rows, kind in ((candidates, ResearchCandidate), (tasks, PlannedQueryTask)):
        if (
            not isinstance(rows, tuple)
            or len(rows) > 8
            or any(not isinstance(row, kind) for row in rows)
        ):
            raise ValueError("Provide at most eight immutable candidates and tasks")
        if len({row.id for row in rows}) != len(rows):
            raise ValueError("Candidate and task identifiers must be unique")
    ids = {row.id for row in candidates}
    if any(row.candidate_id is not None and row.candidate_id not in ids for row in tasks):
        raise ValueError("Planned task references an unknown candidate")
    if source_ids is not None and any(row.source_id not in source_ids for row in tasks):
        raise ValueError("Planned tasks must use selected sources")


def validate_task_receipt(task_id: str | None, purpose: str, candidate_id: str | None) -> None:
    if task_id is not None and (
        not isinstance(task_id, str)
        or not 1 <= len(task_id) <= 128
        or any(ord(c) < 32 or ord(c) == 127 for c in task_id)
    ):
        raise ValueError("Invalid frozen task identity")
    if purpose not in {"baseline", "challenge", "disambiguation"}:
        raise ValueError("Invalid frozen task purpose")
    if candidate_id is not None and not _id(candidate_id):
        raise ValueError("Invalid frozen candidate reference")
    if purpose != "baseline" and task_id is None:
        raise ValueError("Operator task receipts require task identity")
    if purpose == "disambiguation" and candidate_id is None:
        raise ValueError("Disambiguation receipts require a candidate reference")


def task_identity(task: PlannedQueryTask) -> str:
    return f"{task.origin}:{task.id}"
