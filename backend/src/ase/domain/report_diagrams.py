"""Structured, evidence-traceable diagram data a model may request for a report.

The model never emits drawing instructions. It emits bounded rows, nodes, edges or
series, each citing the frozen evidence it rests on, and the application renders them
deterministically. Anything that fails these rules is dropped with a recorded reason
rather than shown half-built.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import StrEnum


class DiagramKind(StrEnum):
    TIMELINE = "timeline"
    ACTOR_MAP = "actor_map"
    CAUSAL_CHAIN = "causal_chain"
    COMPARISON_MATRIX = "comparison_matrix"
    QUANTITATIVE_SERIES = "quantitative_series"


MAX_NODES = 12
MAX_EDGES = 20
MAX_ENTRIES = 12
MAX_ROWS = 8
MAX_COLUMNS = 5
MAX_SERIES = 4
MAX_POINTS = 12
MAX_LABEL_CHARS = 80
MAX_DETAIL_CHARS = 160
MAX_TITLE_CHARS = 120
MAX_CAPTION_CHARS = 300
MAX_ALT_CHARS = 900
MAX_ELEMENT_EVIDENCE = 6
MAX_VALUE = 1e12

_LINK = re.compile(
    r"[a-z][a-z0-9+.-]*://|\b(?:javascript|data|mailto|file):"
    r"|\[[^\]]*\]\([^)]*\)|(?<!:)//[a-z0-9]",
    re.IGNORECASE,
)
_NODE_ID = re.compile(r"^N[1-9][0-9]{0,2}$")


class DiagramRejected(ValueError):
    """A requested diagram is unsupported; the reason is recorded, nothing is drawn."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _text(value: object, limit: int, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise DiagramRejected("diagram text must be a string")
    cleaned = " ".join(value.split())
    if required and not cleaned:
        raise DiagramRejected("diagram text is empty")
    if len(cleaned) > limit:
        raise DiagramRejected("diagram text exceeds its length limit")
    if any(character in cleaned for character in "<>") or _LINK.search(cleaned):
        raise DiagramRejected("diagram text must not contain markup or links")
    return cleaned


def check_evidence(value: tuple[str, ...]) -> None:
    if not value or len(value) > MAX_ELEMENT_EVIDENCE:
        raise DiagramRejected("every diagram element cites one to six pieces of evidence")
    for label in value:
        _text(label, 32)
    if len(set(value)) != len(value):
        raise DiagramRejected("diagram citations must be unique")


def _value(raw: object) -> float:
    if isinstance(raw, bool) or not isinstance(raw, int | float):
        raise DiagramRejected("diagram values must be numbers")
    number = float(raw)
    if not math.isfinite(number) or abs(number) > MAX_VALUE:
        raise DiagramRejected("diagram values must be finite and bounded")
    return number


@dataclass(frozen=True, slots=True)
class DiagramNode:
    id: str
    label: str
    detail: str = ""
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _NODE_ID.match(self.id):
            raise DiagramRejected("diagram node identifiers must be N1 to N999")
        _text(self.label, MAX_LABEL_CHARS)
        _text(self.detail, MAX_DETAIL_CHARS, required=False)
        check_evidence(self.evidence)


@dataclass(frozen=True, slots=True)
class DiagramEdge:
    source: str
    target: str
    label: str = ""
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _NODE_ID.match(self.source) or not _NODE_ID.match(self.target):
            raise DiagramRejected("diagram edges must join declared nodes")
        if self.source == self.target:
            raise DiagramRejected("a diagram edge cannot join a node to itself")
        _text(self.label, MAX_LABEL_CHARS, required=False)
        check_evidence(self.evidence)


@dataclass(frozen=True, slots=True)
class DiagramEntry:
    when: str
    label: str
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.when, 40)
        _text(self.label, MAX_DETAIL_CHARS)
        check_evidence(self.evidence)


@dataclass(frozen=True, slots=True)
class DiagramRow:
    label: str
    cells: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.label, MAX_LABEL_CHARS)
        if not 1 <= len(self.cells) <= MAX_COLUMNS:
            raise DiagramRejected("a comparison row must match the declared columns")
        for cell in self.cells:
            _text(cell, MAX_DETAIL_CHARS, required=False)
        check_evidence(self.evidence)


@dataclass(frozen=True, slots=True)
class DiagramPoint:
    label: str
    value: float

    def __post_init__(self) -> None:
        _text(self.label, 40)
        _value(self.value)


@dataclass(frozen=True, slots=True)
class DiagramSeries:
    label: str
    points: tuple[DiagramPoint, ...] = ()
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _text(self.label, MAX_LABEL_CHARS)
        if not 2 <= len(self.points) <= MAX_POINTS:
            raise DiagramRejected("a series needs between two and twelve points")
        check_evidence(self.evidence)


@dataclass(frozen=True, slots=True)
class ReportDiagram:
    """One bounded diagram: structured data plus the text a reader gets instead."""

    kind: DiagramKind
    title: str
    caption: str
    alt_text: str
    unit: str = ""
    columns: tuple[str, ...] = ()
    nodes: tuple[DiagramNode, ...] = ()
    edges: tuple[DiagramEdge, ...] = ()
    entries: tuple[DiagramEntry, ...] = ()
    rows: tuple[DiagramRow, ...] = ()
    series: tuple[DiagramSeries, ...] = ()

    def __post_init__(self) -> None:
        _text(self.title, MAX_TITLE_CHARS)
        _text(self.caption, MAX_CAPTION_CHARS, required=False)
        _text(self.alt_text, MAX_ALT_CHARS)
        _text(self.unit, 40, required=False)
        _check_shape(self)

    def evidence_labels(self) -> tuple[str, ...]:
        labels: list[str] = []
        for group in (self.nodes, self.edges, self.entries, self.rows, self.series):
            for element in group:
                labels.extend(element.evidence)
        return tuple(dict.fromkeys(labels))


_SHAPES: dict[DiagramKind, frozenset[str]] = {
    DiagramKind.TIMELINE: frozenset({"entries"}),
    DiagramKind.ACTOR_MAP: frozenset({"nodes", "edges"}),
    DiagramKind.CAUSAL_CHAIN: frozenset({"nodes", "edges"}),
    DiagramKind.COMPARISON_MATRIX: frozenset({"columns", "rows"}),
    DiagramKind.QUANTITATIVE_SERIES: frozenset({"series"}),
}
_COLLECTIONS = ("columns", "nodes", "edges", "entries", "rows", "series")


def _check_shape(diagram: ReportDiagram) -> None:  # noqa: PLR0912 - one branch per kind
    allowed = _SHAPES[diagram.kind]
    for name in _COLLECTIONS:
        if getattr(diagram, name) and name not in allowed:
            raise DiagramRejected(f"a {diagram.kind.value} diagram cannot carry {name}")
    if diagram.kind is DiagramKind.TIMELINE:
        if not 3 <= len(diagram.entries) <= MAX_ENTRIES:
            raise DiagramRejected("a timeline needs between three and twelve entries")
        return
    if diagram.kind is DiagramKind.COMPARISON_MATRIX:
        if not 2 <= len(diagram.columns) <= MAX_COLUMNS:
            raise DiagramRejected("a comparison matrix needs two to five columns")
        for column in diagram.columns:
            _text(column, MAX_LABEL_CHARS)
        if not 2 <= len(diagram.rows) <= MAX_ROWS:
            raise DiagramRejected("a comparison matrix needs two to eight rows")
        if any(len(row.cells) != len(diagram.columns) for row in diagram.rows):
            raise DiagramRejected("every comparison row must fill the declared columns")
        return
    if diagram.kind is DiagramKind.QUANTITATIVE_SERIES:
        if not 1 <= len(diagram.series) <= MAX_SERIES:
            raise DiagramRejected("a chart needs between one and four series")
        lengths = {len(row.points) for row in diagram.series}
        if len(lengths) != 1:
            raise DiagramRejected("every series must share the same periods")
        first = tuple(point.label for point in diagram.series[0].points)
        if any(tuple(p.label for p in row.points) != first for row in diagram.series):
            raise DiagramRejected("every series must share the same period labels")
        return
    _check_graph(diagram)


def _check_graph(diagram: ReportDiagram) -> None:
    if not 3 <= len(diagram.nodes) <= MAX_NODES:
        raise DiagramRejected("a relationship diagram needs three to twelve nodes")
    identifiers = [node.id for node in diagram.nodes]
    if len(set(identifiers)) != len(identifiers):
        raise DiagramRejected("diagram node identifiers must be unique")
    if not 2 <= len(diagram.edges) <= MAX_EDGES:
        raise DiagramRejected("a relationship diagram needs two to twenty edges")
    known = set(identifiers)
    if any(edge.source not in known or edge.target not in known for edge in diagram.edges):
        raise DiagramRejected("diagram edges must join declared nodes")
    joined = {end for edge in diagram.edges for end in (edge.source, edge.target)}
    if joined != known:
        raise DiagramRejected("every diagram node must take part in a relationship")
    if len({(edge.source, edge.target) for edge in diagram.edges}) != len(diagram.edges):
        raise DiagramRejected("diagram edges must be distinct")


@dataclass(frozen=True, slots=True)
class DiagramOutcome:
    """What the application decided about a requested diagram."""

    diagram: ReportDiagram | None = None
    reason: str = ""
    requested_kind: str = ""
    dropped: tuple[str, ...] = field(default_factory=tuple)


def traceable(diagram: ReportDiagram, labels: frozenset[str]) -> None:
    """Every element must rest on evidence frozen into this report version."""
    unknown = sorted(set(diagram.evidence_labels()) - labels)
    if unknown:
        raise DiagramRejected("diagram cites evidence that is not in this report")
