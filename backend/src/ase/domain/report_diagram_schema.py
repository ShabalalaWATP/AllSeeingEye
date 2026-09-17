"""The wire contract for a requested diagram and the parser that turns it into data.

The schema is the application's, never the model's: a response that does not fit it is
rejected outright, and a response that fits it is still checked against the frozen
evidence before anything is drawn.
"""

from __future__ import annotations

from typing import Any

from ase.domain.report_diagrams import (
    MAX_COLUMNS,
    MAX_DETAIL_CHARS,
    MAX_EDGES,
    MAX_ELEMENT_EVIDENCE,
    MAX_ENTRIES,
    MAX_LABEL_CHARS,
    MAX_NODES,
    MAX_POINTS,
    MAX_ROWS,
    MAX_SERIES,
    MAX_VALUE,
    DiagramEdge,
    DiagramEntry,
    DiagramKind,
    DiagramNode,
    DiagramPoint,
    DiagramRejected,
    DiagramRow,
    DiagramSeries,
    ReportDiagram,
    traceable,
)

_EVIDENCE: dict[str, Any] = {
    "type": "array",
    "minItems": 1,
    "maxItems": MAX_ELEMENT_EVIDENCE,
    "items": {
        "type": "string",
        "minLength": 1,
        "maxLength": 32,
        "pattern": "^E[1-9][0-9]*$",
        "description": "Exact supplied evidence ID only, for example E1.",
    },
}


def _string(limit: int, *, required: bool = True) -> dict[str, Any]:
    return {"type": "string", "minLength": int(required), "maxLength": limit}


def _object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": list(properties),
        "properties": properties,
    }


def _array(items: dict[str, Any], maximum: int) -> dict[str, Any]:
    return {"type": "array", "minItems": 0, "maxItems": maximum, "items": items}


DIAGRAM_SCHEMA: dict[str, Any] = _object(
    {
        "kind": {"type": "string", "enum": [kind.value for kind in DiagramKind]},
        "title": _string(120),
        "caption": _string(300, required=False),
        "alt_text": _string(900),
        "unit": _string(40, required=False),
        "columns": _array(_string(MAX_LABEL_CHARS), MAX_COLUMNS),
        "nodes": _array(
            _object(
                {
                    "id": {
                        "type": "string",
                        "minLength": 2,
                        "maxLength": 4,
                        "pattern": "^N[0-9]+$",
                    },
                    "label": _string(MAX_LABEL_CHARS),
                    "detail": _string(MAX_DETAIL_CHARS, required=False),
                    "evidence": _EVIDENCE,
                }
            ),
            MAX_NODES,
        ),
        "edges": _array(
            _object(
                {
                    "source": {"type": "string", "minLength": 2, "maxLength": 4},
                    "target": {"type": "string", "minLength": 2, "maxLength": 4},
                    "label": _string(MAX_LABEL_CHARS, required=False),
                    "evidence": _EVIDENCE,
                }
            ),
            MAX_EDGES,
        ),
        "entries": _array(
            _object(
                {
                    "when": _string(40),
                    "label": _string(MAX_DETAIL_CHARS),
                    "evidence": _EVIDENCE,
                }
            ),
            MAX_ENTRIES,
        ),
        "rows": _array(
            _object(
                {
                    "label": _string(MAX_LABEL_CHARS),
                    "cells": _array(_string(MAX_DETAIL_CHARS, required=False), MAX_COLUMNS),
                    "evidence": _EVIDENCE,
                }
            ),
            MAX_ROWS,
        ),
        "series": _array(
            _object(
                {
                    "label": _string(MAX_LABEL_CHARS),
                    "points": _array(
                        _object(
                            {
                                "label": _string(40),
                                "value": {
                                    "type": "number",
                                    "minimum": -MAX_VALUE,
                                    "maximum": MAX_VALUE,
                                },
                            }
                        ),
                        MAX_POINTS,
                    ),
                    "evidence": _EVIDENCE,
                }
            ),
            MAX_SERIES,
        ),
    }
)

NULLABLE_DIAGRAM_SCHEMA: dict[str, Any] = {
    **DIAGRAM_SCHEMA,
    "type": ["object", "null"],
    "description": (
        "Request a diagram only when it carries something the prose cannot. Use null "
        "otherwise. Supply structured data only; never drawing or styling instructions."
    ),
}


def parse_diagram(data: Any, labels: frozenset[str]) -> ReportDiagram:
    """Build a validated diagram, or raise ``DiagramRejected`` with a recorded reason."""
    if not isinstance(data, dict):
        raise DiagramRejected("diagram payload is not an object")
    try:
        kind = DiagramKind(str(data.get("kind", "")))
    except ValueError:
        raise DiagramRejected("unsupported diagram kind") from None
    diagram = ReportDiagram(
        kind=kind,
        title=_raw(data, "title"),
        caption=_raw(data, "caption"),
        alt_text=_raw(data, "alt_text"),
        unit=_raw(data, "unit"),
        columns=tuple(_strings(data.get("columns"))),
        nodes=tuple(
            DiagramNode(_raw(row, "id"), _raw(row, "label"), _raw(row, "detail"), _labels(row))
            for row in _rows(data, "nodes")
        ),
        edges=tuple(
            DiagramEdge(_raw(row, "source"), _raw(row, "target"), _raw(row, "label"), _labels(row))
            for row in _rows(data, "edges")
        ),
        entries=tuple(
            DiagramEntry(_raw(row, "when"), _raw(row, "label"), _labels(row))
            for row in _rows(data, "entries")
        ),
        rows=tuple(
            DiagramRow(_raw(row, "label"), tuple(_strings(row.get("cells"))), _labels(row))
            for row in _rows(data, "rows")
        ),
        series=tuple(
            DiagramSeries(
                _raw(row, "label"),
                tuple(
                    DiagramPoint(_raw(point, "label"), _number(point.get("value")))
                    for point in _rows(row, "points")
                ),
                _labels(row),
            )
            for row in _rows(data, "series")
        ),
    )
    traceable(diagram, labels)
    return diagram


def _raw(data: Any, key: str) -> str:
    value = data.get(key, "") if isinstance(data, dict) else ""
    if value is None:
        return ""
    if not isinstance(value, str):
        raise DiagramRejected(f"diagram {key} must be text")
    return " ".join(value.split())


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise DiagramRejected("diagram list fields must be arrays")
    return [item if isinstance(item, str) else _reject() for item in value]


def _rows(data: Any, key: str) -> list[Any]:
    value = data.get(key) if isinstance(data, dict) else None
    if value is None:
        return []
    if not isinstance(value, list):
        raise DiagramRejected("diagram list fields must be arrays")
    return value


def _labels(row: Any) -> tuple[str, ...]:
    value = row.get("evidence") if isinstance(row, dict) else None
    if not isinstance(value, list) or not value:
        raise DiagramRejected("every diagram element must cite evidence")
    labels = tuple(item if isinstance(item, str) else _reject() for item in value)
    if len(set(labels)) != len(labels):
        raise DiagramRejected("diagram citations must be unique")
    return labels


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise DiagramRejected("diagram values must be numbers")
    return float(value)


def _reject() -> str:
    raise DiagramRejected("diagram text must be a string")
