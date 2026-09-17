"""Rebuild saved diagram rows; a stored row that no longer validates is dropped."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ase.domain.report_diagrams import (
    DiagramEdge,
    DiagramEntry,
    DiagramKind,
    DiagramNode,
    DiagramPoint,
    DiagramRejected,
    DiagramRow,
    DiagramSeries,
    ReportDiagram,
)

MAX_DIAGRAM_ROWS = 20


def restore_diagrams(value: object) -> tuple[ReportDiagram, ...]:
    """Restore saved diagrams; a stored row that no longer validates is dropped."""
    if not isinstance(value, list):
        return ()
    restored: list[ReportDiagram] = []
    for item in value[:MAX_DIAGRAM_ROWS]:
        try:
            restored.append(_diagram(item))
        except (DiagramRejected, ValueError, TypeError, KeyError, AttributeError):
            continue
    return tuple(restored)


def _diagram(item: Any) -> ReportDiagram:
    if not isinstance(item, Mapping):
        raise DiagramRejected("diagrams must be objects")
    return ReportDiagram(
        kind=DiagramKind(str(item["kind"])),
        title=str(item.get("title", "")),
        caption=str(item.get("caption", "")),
        alt_text=str(item.get("alt_text", "")),
        unit=str(item.get("unit", "")),
        columns=tuple(str(value) for value in item.get("columns", ())),
        nodes=tuple(
            DiagramNode(
                str(row["id"]),
                str(row["label"]),
                str(row.get("detail", "")),
                tuple(str(label) for label in row.get("evidence", ())),
            )
            for row in item.get("nodes", ())
        ),
        edges=tuple(
            DiagramEdge(
                str(row["source"]),
                str(row["target"]),
                str(row.get("label", "")),
                tuple(str(label) for label in row.get("evidence", ())),
            )
            for row in item.get("edges", ())
        ),
        entries=tuple(
            DiagramEntry(
                str(row["when"]),
                str(row["label"]),
                tuple(str(label) for label in row.get("evidence", ())),
            )
            for row in item.get("entries", ())
        ),
        rows=tuple(
            DiagramRow(
                str(row["label"]),
                tuple(str(cell) for cell in row.get("cells", ())),
                tuple(str(label) for label in row.get("evidence", ())),
            )
            for row in item.get("rows", ())
        ),
        series=tuple(
            DiagramSeries(
                str(row["label"]),
                tuple(
                    DiagramPoint(str(point["label"]), float(point["value"]))
                    for point in row.get("points", ())
                ),
                tuple(str(label) for label in row.get("evidence", ())),
            )
            for row in item.get("series", ())
        ),
    )
