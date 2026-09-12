"""Assemble existing report fields without asking a model to rewrite topic text."""

from typing import Any

from ase.application.reports.sections.planning import Topic
from ase.application.reports.sections.quality import (
    ensure_requirement_coverage,
    normalise_gap_rows,
    requirement_support_from_topics,
)
from ase.domain.direction import Direction
from ase.domain.report_input import parse_model_body
from ase.domain.reports import ReportBody


def assemble(
    topics: list[tuple[Topic, dict[str, Any]]],
    synthesis: dict[str, Any],
    direction: Direction | None = None,
) -> ReportBody:
    reporting: list[dict[str, Any]] = []
    assessment: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for topic, section in topics:
        if section["reporting"]:
            reporting.append({"theme": topic.title, "items": section["reporting"]})
        assessment.extend({**row, "heading": topic.title} for row in section["assessment"])
        gaps.extend(section["gaps"])
    gaps.extend(synthesis["gaps"])
    report = parse_model_body(
        {
            **synthesis,
            "reporting": reporting,
            "assessment": assessment,
            "gaps": normalise_gap_rows(gaps),
        }
    )
    report, _ = ensure_requirement_coverage(
        report,
        direction,
        supported=requirement_support_from_topics(topics),
    )
    return report
