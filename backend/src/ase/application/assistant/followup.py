"""Filter an already bounded personal continuation packet without fresh retrieval."""

import re
from dataclasses import replace
from datetime import datetime

from ase.application.assistant.intent import interpret_question
from ase.domain.assistant import AssistantContext, AssistantInterpretation, AssistantQuestion
from ase.domain.events import Category


def followup_context(
    previous: AssistantContext, question: AssistantQuestion, now: datetime
) -> AssistantContext:
    intent = interpret_question(question.question, now=now)
    period = question.time_range or intent.time_range
    effective_categories = question.source_categories or (
        *(category.value for category in Category),
        "camera",
        "infrastructure",
        "doctrine",
    )
    interpretation = AssistantInterpretation(
        intent.topics,
        intent.countries,
        period.since if period else None,
        period.until if period else None,
        notes=("Reusing evidence from this user's earlier Ask Eye answer.",),
        source_categories=effective_categories,
    )
    if intent.clarification:
        return AssistantContext(
            (),
            0,
            0,
            False,
            ("No previous sources searched because the follow-up needs clarification.",),
            clarification=intent.clarification,
            interpretation=interpretation,
        )
    # Pronouns refer to the frozen evidence set. Analytical wording such as
    # "independently confirmed" is not a new entity that each title must contain.
    filter_intent = replace(
        intent,
        terms=tuple(term for term in intent.terms if term != "military"),
        anchors=(),
        residual=(),
    )
    rows = [
        source
        for source in previous.sources
        if _source_category(source) in effective_categories
        and filter_intent.accepts(_source_category(source), source)
        and (
            period is None
            or (
                source.published_at is not None
                and period.since <= source.published_at < period.until
            )
        )
        and (
            question.bbox is None
            or (source.point is not None and question.bbox.contains(source.point))
        )
        and (
            question.selected is None
            or (source.kind == question.selected.kind and source.record_id == question.selected.id)
        )
    ]
    return AssistantContext(
        tuple(replace(row, id=f"E{index + 1}") for index, row in enumerate(rows)),
        len(previous.sources),
        len({row.source_id for row in rows}),
        previous.capped,
        (
            *previous.notes,
            "Follow-up uses a frozen evidence packet; source status is rechecked.",
        ),
        matched_count=len(rows),
        interpretation=interpretation,
    )


def _source_category(source: object) -> str:
    kind = getattr(source, "kind", "")
    if kind != "event":
        return str(kind)
    for detail in getattr(source, "details", ()):
        match = re.match(r"Category: ([a-z_]+);", detail)
        if match:
            return match.group(1)
    return "event"
