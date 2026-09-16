"""The wire contract for the dedicated analysis pass and its strict boundary checks.

The pass reads the drafted reporting and the frozen evidence and returns assessment
prose plus, at most, one requested diagram. Everything it returns is checked against the
frozen evidence before it reaches a report: unknown citations are stripped, a section
left without support is dropped, and a diagram that fails validation is refused with a
recorded reason rather than shown half-built.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ase.domain.doctrine import find_urls
from ase.domain.report_diagram_schema import NULLABLE_DIAGRAM_SCHEMA, parse_diagram
from ase.domain.report_diagrams import DiagramRejected, ReportDiagram
from ase.domain.report_input import _check
from ase.domain.reports import MAX_SECTION_CHARS, AssessmentSection, ReportParseError

MAX_ANALYSIS_SECTIONS = 6
MIN_ANALYSIS_SECTIONS = 1
MAX_RESPONSE_BYTES = 128 * 1024

ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["sections", "diagram"],
    "properties": {
        "sections": {
            "type": "array",
            "minItems": MIN_ANALYSIS_SECTIONS,
            "maxItems": MAX_ANALYSIS_SECTIONS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["heading", "text", "evidence"],
                "properties": {
                    "heading": {"type": "string", "minLength": 1, "maxLength": 120},
                    "text": {"type": "string", "minLength": 1, "maxLength": MAX_SECTION_CHARS},
                    "evidence": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 12,
                        "items": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 32,
                            "pattern": "^E[1-9][0-9]*$",
                        },
                    },
                },
            },
        },
        "diagram": NULLABLE_DIAGRAM_SCHEMA,
    },
}


class AnalysisRejected(ValueError):
    """The analysis response cannot be used; the report keeps its drafted body."""


def parse_analysis(
    value: Any,
    labels: frozenset[str],
    urls: Mapping[str, str | None],
) -> tuple[tuple[AssessmentSection, ...], ReportDiagram | None, str]:
    """Return the usable sections, any accepted diagram, and why a diagram was refused."""
    try:
        _check(value, ANALYSIS_SCHEMA, "analysis")
    except ReportParseError as exc:
        raise AnalysisRejected(f"{exc}"[:300]) from None
    sections = _sections(value["sections"], labels, urls)
    if not sections:
        raise AnalysisRejected("no analysis section rested on this report's evidence")
    diagram, reason = _diagram(value.get("diagram"), labels)
    return sections, diagram, reason


def _sections(
    rows: Sequence[Any],
    labels: frozenset[str],
    urls: Mapping[str, str | None],
) -> tuple[AssessmentSection, ...]:
    kept: list[AssessmentSection] = []
    for row in rows:
        evidence = tuple(dict.fromkeys(item for item in row["evidence"] if item in labels))
        if not evidence:
            continue
        text = str(row["text"]).strip()
        heading = str(row["heading"]).strip()
        if _unsafe(text, evidence, urls) or _unsafe(heading, evidence, urls):
            continue
        kept.append(AssessmentSection(heading=heading, text=text, evidence=evidence))
    return tuple(kept)


def _unsafe(text: str, evidence: Sequence[str], urls: Mapping[str, str | None]) -> bool:
    if "<" in text or ">" in text:
        return True
    allowed = {url for label, url in urls.items() if url and label in evidence}
    return any(url.rstrip(".,") not in allowed for url in find_urls(text))


def _diagram(raw: Any, labels: frozenset[str]) -> tuple[ReportDiagram | None, str]:
    if raw is None:
        return None, ""
    try:
        return parse_diagram(raw, labels), ""
    except DiagramRejected as exc:
        return None, exc.reason[:200]
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return None, "the requested diagram did not fit the diagram contract"
