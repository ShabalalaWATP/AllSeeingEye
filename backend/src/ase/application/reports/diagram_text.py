"""The text a reader gets instead of the picture: an equivalent table, always produced.

Accessibility is not optional here. Every diagram carries a text alternative and an
equivalent table, so the report reads correctly without images, in a screen reader, and
in exports that cannot show vector drawings.
"""

from __future__ import annotations

from dataclasses import dataclass

from ase.application.reports.export_text import plain_markdown
from ase.domain.report_diagrams import DiagramKind, ReportDiagram

SOURCE_COLUMN = "Source"


@dataclass(frozen=True, slots=True)
class DiagramProjection:
    """The diagram as a table: cell text plus the evidence labels for its final column."""

    title: str
    caption: str
    columns: tuple[str, ...]
    rows: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...]


def project_diagram(diagram: ReportDiagram) -> DiagramProjection:
    columns, rows = _shape(diagram)
    return DiagramProjection(
        title=diagram.title,
        caption=_caption(diagram),
        columns=(*columns, SOURCE_COLUMN),
        rows=rows,
    )


def _caption(diagram: ReportDiagram) -> str:
    kind = diagram.kind.value.replace("_", " ")
    caption = diagram.caption or f"Generated {kind} built only from the cited evidence."
    if diagram.unit:
        caption = f"{caption} Values are reported in {diagram.unit} exactly as sourced."
    return caption


def _shape(
    diagram: ReportDiagram,
) -> tuple[tuple[str, ...], tuple[tuple[tuple[str, ...], tuple[str, ...]], ...]]:
    if diagram.kind is DiagramKind.TIMELINE:
        return ("When", "What was reported"), tuple(
            ((entry.when, entry.label), entry.evidence) for entry in diagram.entries
        )
    if diagram.kind is DiagramKind.COMPARISON_MATRIX:
        return ("", *diagram.columns), tuple(
            ((row.label, *row.cells), row.evidence) for row in diagram.rows
        )
    if diagram.kind is DiagramKind.QUANTITATIVE_SERIES:
        periods = tuple(point.label for point in diagram.series[0].points)
        return ("Series", *periods), tuple(
            ((row.label, *(_number(point.value) for point in row.points)), row.evidence)
            for row in diagram.series
        )
    return _graph(diagram)


def _graph(
    diagram: ReportDiagram,
) -> tuple[tuple[str, ...], tuple[tuple[tuple[str, ...], tuple[str, ...]], ...]]:
    names = {node.id: _name(node.label, node.detail) for node in diagram.nodes}
    rows = [
        (
            (names[edge.source], edge.label or "is linked to", names[edge.target]),
            edge.evidence,
        )
        for edge in diagram.edges
    ]
    return ("From", "Relationship", "To"), tuple(rows)


def _name(label: str, detail: str) -> str:
    return f"{label} ({detail})" if detail else label


def _number(value: float) -> str:
    return f"{value:g}"


def diagram_lines(diagram: ReportDiagram) -> list[str]:
    """The diagram as Markdown: heading, text alternative, then the equivalent table."""
    projection = project_diagram(diagram)
    lines = [f"### {plain_markdown(projection.title)}", "", plain_markdown(diagram.alt_text), ""]
    lines.append("| " + " | ".join(plain_markdown(value) for value in projection.columns) + " |")
    lines.append("| " + " | ".join("---" for _ in projection.columns) + " |")
    for cells, evidence in projection.rows:
        values = (*cells, ", ".join(evidence))
        lines.append("| " + " | ".join(plain_markdown(value) for value in values) + " |")
    lines.extend(("", f"*{plain_markdown(projection.caption)}*", ""))
    return lines
