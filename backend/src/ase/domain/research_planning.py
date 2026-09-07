"""Frozen automatic planning proposals and admission, never proof of collection."""

from dataclasses import dataclass, fields
from typing import Any, Literal

from ase.domain.research_continuation import bounded_text
from ase.domain.research_tasks import (
    PlannedQueryTask,
    ResearchCandidate,
    candidate_from_dict,
    task_identity,
)

PlanningStatus = Literal["applied", "empty", "rejected", "unavailable", "skipped"]


@dataclass(frozen=True, slots=True)
class PlanningTrace:
    status: PlanningStatus
    requested_model: str
    returned_model: str
    call_count: int
    reason: str
    proposed_candidates: tuple[ResearchCandidate, ...] = ()
    proposed_tasks: tuple[PlannedQueryTask, ...] = ()
    accepted_candidate_ids: tuple[str, ...] = ()
    accepted_task_ids: tuple[str, ...] = ()
    policy_version: str = "ase-model-plan-v1"

    def __post_init__(self) -> None:
        if (
            self.status not in {"applied", "empty", "rejected", "unavailable", "skipped"}
            or self.policy_version != "ase-model-plan-v1"
        ):
            raise ValueError("Invalid automatic planning status")
        if type(self.call_count) is not int or self.call_count not in {0, 1}:
            raise ValueError("Invalid planning call count")
        if not all(
            bounded_text(value, 2048, empty=True)
            for value in (self.requested_model, self.returned_model)
        ) or not bounded_text(self.reason, 500):
            raise ValueError("Invalid planning metadata")
        for rows, kind in (
            (self.proposed_candidates, ResearchCandidate),
            (self.proposed_tasks, PlannedQueryTask),
        ):
            if (
                not isinstance(rows, tuple)
                or len(rows) > 8
                or any(not isinstance(row, kind) or row.origin != "model" for row in rows)
            ):
                raise ValueError("Invalid model proposals")
            if len({row.id for row in rows}) != len(rows):
                raise ValueError("Duplicate model proposal identifiers")
        for identifiers in (self.accepted_candidate_ids, self.accepted_task_ids):
            if (
                not isinstance(identifiers, tuple)
                or len(identifiers) > 8
                or any(not bounded_text(identifier, 128) for identifier in identifiers)
            ):
                raise ValueError("Invalid accepted planning identifiers")
        expected = (
            tuple(row.id for row in self.proposed_candidates),
            tuple(task_identity(row) for row in self.proposed_tasks),
        )
        actual = (self.accepted_candidate_ids, self.accepted_task_ids)
        if self.status == "applied":
            if actual != expected or not any(actual) or self.call_count != 1:
                raise ValueError("Invalid accepted planning proposals")
        elif any(actual):
            raise ValueError("Unaccepted planning proposals cannot be marked accepted")
        if self.status == "skipped" and self.call_count != 0:
            raise ValueError("Skipped planning cannot have a model call")


def planning_from_dict(data: Any) -> PlanningTrace | None:
    if data is None:
        return None
    if type(data) is not dict or set(data) != {field.name for field in fields(PlanningTrace)}:
        raise ValueError("Invalid saved automatic planning fields")
    values = dict(data)
    for key, kind in (
        ("proposed_candidates", ResearchCandidate),
        ("proposed_tasks", PlannedQueryTask),
    ):
        rows = data[key]
        if not isinstance(rows, (tuple, list)) or len(rows) > 8:
            raise ValueError("Invalid saved planning proposals")
        field = "identifiers" if key == "proposed_candidates" else "terms"
        expected = {item.name for item in fields(kind)}
        required = expected - (
            {"registry_identifiers"} if key == "proposed_candidates" else {"route", "identifier_id"}
        )
        if any(
            type(row) is not dict
            or not required <= set(row) <= expected
            or not isinstance(row[field], (tuple, list))
            for row in rows
        ):
            raise ValueError("Invalid saved planning proposal fields")
        values[key] = tuple(
            candidate_from_dict(row)
            if key == "proposed_candidates"
            else kind(**{**row, field: tuple(row[field])})
            for row in rows
        )
    for key in ("accepted_candidate_ids", "accepted_task_ids"):
        if not isinstance(data[key], (tuple, list)) or len(data[key]) > 8:
            raise ValueError("Invalid saved planning selection")
        values[key] = tuple(data[key])
    return PlanningTrace(**values)
