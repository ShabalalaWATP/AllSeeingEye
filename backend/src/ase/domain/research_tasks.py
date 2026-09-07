"""Operator hypotheses are search context, never verified entity matches."""

import re
from dataclasses import dataclass
from typing import Any, Literal

from ase.domain.registry_identifiers import RegistryIdentifier, registry_subject

TaskPurpose = Literal["baseline", "challenge", "disambiguation"]


def _id(value: object) -> bool:
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

    registry_identifiers: tuple[RegistryIdentifier, ...] = ()

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
        if (
            not isinstance(self.registry_identifiers, tuple)
            or len(self.registry_identifiers) + len(self.identifiers) > 8
            or any(not isinstance(row, RegistryIdentifier) for row in self.registry_identifiers)
            or sum(len(row.value) for row in self.registry_identifiers)
            + sum(map(len, self.identifiers))
            > 1000
        ):
            raise ValueError("Provide at most eight bounded candidate identifiers")
        if self.origin == "model" and self.registry_identifiers:
            raise ValueError("Models may select operator identifiers, never supply registry values")
        if len({row.id for row in self.registry_identifiers}) != len(self.registry_identifiers):
            raise ValueError("Duplicate registry identifier reference")
        if len(
            {
                (row.namespace, registry_subject(row.namespace, row.value))
                for row in self.registry_identifiers
            }
        ) != len(self.registry_identifiers):
            raise ValueError("Duplicate canonical registry identifier")


@dataclass(frozen=True, slots=True)
class PlannedQueryTask:
    id: str
    source_id: str
    purpose: Literal["challenge", "disambiguation"]
    terms: tuple[str, ...]
    candidate_id: str | None = None
    origin: Literal["operator", "model"] = "operator"

    route: Literal["terms", "candidate_identifier"] = "terms"
    identifier_id: str | None = None

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
        if self.route == "terms":
            if not self.terms or self.identifier_id is not None:
                raise ValueError("Term tasks require search terms and no registry reference")
        elif self.route == "candidate_identifier":
            if self.terms or self.purpose != "disambiguation" or not _id(self.identifier_id):
                raise ValueError(
                    "Exact lookups require disambiguation, one identifier reference and no terms"
                )
        else:
            raise ValueError("Unknown planned task route")


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
    for task in tasks:
        if task.route == "candidate_identifier":
            candidate = next((row for row in candidates if row.id == task.candidate_id), None)
            if (
                candidate is None
                or candidate.origin != "operator"
                or not any(row.id == task.identifier_id for row in candidate.registry_identifiers)
            ):
                raise ValueError("Exact lookup requires an operator-supplied candidate identifier")
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


def candidate_from_dict(row: dict[str, Any]) -> ResearchCandidate:
    return ResearchCandidate(
        **{
            **row,
            "identifiers": tuple(row.get("identifiers", ())),
            "registry_identifiers": tuple(
                RegistryIdentifier(**item) for item in row.get("registry_identifiers", ())
            ),
        }
    )


def validate_registry_scope(tasks: tuple[PlannedQueryTask, ...], allowed: bool) -> None:
    if not allowed and any(task.route == "candidate_identifier" for task in tasks):
        raise ValueError("Exact registry tasks require company research without an area")
