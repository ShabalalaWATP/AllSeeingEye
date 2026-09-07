"""Bounded proposals are admitted through the same concrete provider plan as operator tasks."""

import json
from dataclasses import asdict, replace
from typing import Any, cast

from ase.application.ports.research import ResearchCollection
from ase.domain.research import ResearchQuery
from ase.domain.research_area import area_to_dict
from ase.domain.research_plan import ResearchPlan
from ase.domain.research_planning import PlanningTrace
from ase.domain.research_tasks import PlannedQueryTask, ResearchCandidate, task_identity

MAX_CONTEXT_BYTES = 32 * 1024
MAX_OUTPUT_BYTES = 32 * 1024


def planning_context(
    query: ResearchQuery,
    plan: ResearchPlan,
    seed_count: int,
    *,
    operator_terms: tuple[str, ...] = (),
) -> dict[str, Any]:
    if query.area and len(query.area.geometry.canonical_json.encode("utf-8")) > 16 * 1024:
        raise ValueError("Area geometry exceeds the planning input budget")
    eligible = [
        task
        for task in plan.tasks
        if task.purpose == "baseline"
        and task.selected
        and ((task.supported and task.planned_terms_supported) or task.registry_options)
    ]
    task_slots = min(
        8 - len(query.planned_tasks),
        64 - len(plan.tasks),
        64 - sum(task.selected for task in plan.tasks) - seed_count,
    )
    result = {
        "question": query.question,
        "terms": query.terms,
        "subject": query.subject,
        "country_iso": query.country_iso,
        "languages": query.languages,
        "since": query.since.isoformat(),
        "until": query.until.isoformat(),
        "time_basis": query.effective_time_basis.value,
        "area": area_to_dict(query.area),
        "identifier_context": [
            query.question,
            query.subject or "",
            *operator_terms,
            *(row.label for row in query.candidate_hypotheses if row.origin == "operator"),
            *(
                value
                for row in query.candidate_hypotheses
                if row.origin == "operator"
                for value in row.identifiers
            ),
            *(
                value
                for row in query.planned_tasks
                if row.origin == "operator"
                for value in row.terms
            ),
        ],
        "operator_candidates": [asdict(row) for row in query.candidate_hypotheses],
        "operator_tasks": [asdict(row) for row in query.planned_tasks],
        "allowed_sources": [
            {
                "id": row.source_id,
                "name": row.source_name,
                "language": row.language,
                "terms_supported": row.supported and row.planned_terms_supported,
                "identifier_options": [asdict(option) for option in row.registry_options],
            }
            for row in eligible
        ],
        "candidate_slots": 8 - len(query.candidate_hypotheses),
        "task_slots": max(0, task_slots),
    }
    if len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > MAX_CONTEXT_BYTES:
        raise ValueError("Planning context exceeds its fixed input budget")
    return result


def parse_proposals(
    content: str,
) -> tuple[tuple[ResearchCandidate, ...], tuple[PlannedQueryTask, ...]]:
    if len(content.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ValueError("Planning response exceeds its limit")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate planning field")
            result[key] = value
        return result

    payload = json.loads(content, object_pairs_hook=unique_object)
    if type(payload) is not dict or set(payload) != {"candidates", "tasks"}:
        raise ValueError("Invalid planning object")
    result = []
    for key, kind, names, sequence in (
        ("candidates", ResearchCandidate, {"id", "label", "identifiers"}, "identifiers"),
        (
            "tasks",
            PlannedQueryTask,
            {"id", "source_id", "purpose", "terms", "candidate_id"},
            "terms",
        ),
    ):
        rows = payload[key]
        if type(rows) is not list or len(rows) > 8:
            raise ValueError("Invalid proposal count")
        output = []
        for row in rows:
            allowed_names = names | ({"route", "identifier_id"} if key == "tasks" else set())
            if (
                type(row) is not dict
                or not names <= set(row) <= allowed_names
                or type(row[sequence]) is not list
            ):
                raise ValueError("Invalid proposal fields")
            output.append(kind(**{**row, sequence: tuple(row[sequence]), "origin": "model"}))
        if len({row.id for row in output}) != len(output):
            raise ValueError("Duplicate proposal identifiers")
        result.append(tuple(output))
    return cast(tuple[ResearchCandidate, ...], result[0]), cast(
        tuple[PlannedQueryTask, ...], result[1]
    )


def admit_proposals(
    query: ResearchQuery,
    context: dict[str, Any],
    candidates: tuple[ResearchCandidate, ...],
    tasks: tuple[PlannedQueryTask, ...],
    collection: ResearchCollection,
    seed_count: int,
) -> ResearchQuery:
    if len(candidates) > context["candidate_slots"] or len(tasks) > context["task_slots"]:
        raise ValueError("Proposals exceed remaining plan capacity")
    allowed = {row["id"] for row in context["allowed_sources"]}
    if any(task.source_id not in allowed for task in tasks):
        raise ValueError("A proposed source does not support selected task searches")
    for task in tasks:
        source = next(row for row in context["allowed_sources"] if row["id"] == task.source_id)
        if task.route == "candidate_identifier":
            if not any(
                option["candidate_id"] == task.candidate_id
                and option["identifier_id"] == task.identifier_id
                for option in source.get("identifier_options", ())
            ):
                raise ValueError("Model lookup must select an issued operator identifier reference")
        elif not source.get("terms_supported", True):
            raise ValueError("This source supports exact candidate lookup only")
    # Only the supplied question and operator context can ground exact identifiers.
    supplied = context["identifier_context"]
    if any(
        not any(identifier in text for text in supplied)
        for row in candidates
        for identifier in row.identifiers
    ):
        raise ValueError("A proposed identifier is absent from supplied operator context")
    combined = replace(
        query,
        candidate_hypotheses=(*query.candidate_hypotheses, *candidates),
        planned_tasks=(*query.planned_tasks, *tasks),
    )
    plan = collection.plan(combined)
    accepted = {task_identity(row) for row in tasks}
    if sum(row.selected for row in plan.tasks) + seed_count > 64 or any(
        row.task_id in accepted
        and not (
            row.selected
            and row.supported
            and (row.planned_terms_supported or row.registry_lookup is not None)
        )
        for row in plan.tasks
    ):
        raise ValueError("The expanded plan is unsupported or exceeds receipt capacity")
    return combined


def record_planning(plan: ResearchPlan, trace: PlanningTrace) -> ResearchPlan:
    return replace(plan, planning=trace, model_calls=plan.model_calls + trace.call_count)
