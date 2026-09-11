"""Assemble existing report fields without asking a model to rewrite topic text."""

from typing import Any

from ase.application.reports.sections.planning import Topic
from ase.domain.report_input import parse_model_body
from ase.domain.reports import ReportBody


def assemble(topics: list[tuple[Topic, dict[str, Any]]], synthesis: dict[str, Any]) -> ReportBody:
    reporting: list[dict[str, Any]] = []
    assessment: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for topic, body in topics:
        if body["reporting"]:
            reporting.append({"theme": topic.title, "items": body["reporting"]})
        assessment.extend({**row, "heading": topic.title} for row in body["assessment"])
        gaps.extend(body["gaps"])
    gaps.extend(synthesis["gaps"])
    unique: dict[tuple[str | None, str], dict[str, Any]] = {}
    for row in gaps:
        unique.setdefault((row["eei"], row["text"].strip().casefold()), row)
    return parse_model_body(
        {
            **synthesis,
            "reporting": reporting,
            "assessment": assessment,
            "gaps": list(unique.values()),
        }
    )
