"""Deterministic inline SVG for a validated diagram: the application draws, never the model.

The model supplies structured data only. Everything here is generated from that data, so
the same diagram always produces the same bytes, nothing from a source or a model ever
becomes markup, and the drawing cannot say anything the validated data does not.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from ase.domain.report_diagrams import DiagramKind, ReportDiagram

WIDTH = 880
PADDING = 24
ROW_HEIGHT = 46
CHAR_WIDTH = 7.2
FONT = "font-family='system-ui, sans-serif'"
INK = "#101820"
MUTED = "#53616D"
RULE = "#B8C3CC"
ACCENT = "#168A9B"
SERIES_DASH = ("", "6 4", "2 4", "10 4 2 4")


def render_diagram_svg(diagram: ReportDiagram) -> str:
    """One self-contained SVG string, already escaped and bounded."""
    body, height = _body(diagram)
    title, description = escape(diagram.title), escape(diagram.alt_text)
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {WIDTH} {height}' "
        f"width='100%' role='img' aria-label='{_attribute(diagram.alt_text)}' {FONT}>"
        f"<title>{title}</title><desc>{description}</desc>"
        f"<rect x='0' y='0' width='{WIDTH}' height='{height}' fill='none'/>"
        f"{body}</svg>"
    )


def _attribute(value: str) -> str:
    return escape(value, {"'": "&apos;", '"': "&quot;"})


def _text(
    x: float, y: float, value: str, *, size: int = 13, fill: str = INK, weight: str = ""
) -> str:
    style = f" font-weight='{weight}'" if weight else ""
    return (
        f"<text x='{_n(x)}' y='{_n(y)}' font-size='{size}' fill='{fill}'{style}>"
        f"{escape(value)}</text>"
    )


def _n(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _clip(value: str, width: float, size: int = 13) -> str:
    limit = max(4, int(width / (CHAR_WIDTH * size / 13)))
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def _body(diagram: ReportDiagram) -> tuple[str, int]:
    if diagram.kind is DiagramKind.TIMELINE:
        return _timeline(diagram)
    if diagram.kind is DiagramKind.COMPARISON_MATRIX:
        return _matrix(diagram)
    if diagram.kind is DiagramKind.QUANTITATIVE_SERIES:
        return _chart(diagram)
    return _graph(diagram)


def _timeline(diagram: ReportDiagram) -> tuple[str, int]:
    spine = 190
    height = PADDING * 2 + ROW_HEIGHT * len(diagram.entries)
    parts = [
        f"<line x1='{spine}' y1='{PADDING}' x2='{spine}' y2='{height - PADDING}' "
        f"stroke='{RULE}' stroke-width='2'/>"
    ]
    for index, entry in enumerate(diagram.entries):
        y = PADDING + ROW_HEIGHT * index + ROW_HEIGHT / 2
        parts.append(
            _text(
                PADDING,
                y + 4,
                _clip(entry.when, spine - PADDING - 24, 12),
                size=12,
                fill=MUTED,
                weight="600",
            )
        )
        parts.append(f"<circle cx='{spine}' cy='{_n(y)}' r='5' fill='{ACCENT}'/>")
        parts.append(_text(spine + 18, y + 4, _clip(entry.label, WIDTH - spine - 42)))
    return "".join(parts), height


def _matrix(diagram: ReportDiagram) -> tuple[str, int]:
    label_width = 220
    columns = len(diagram.columns)
    cell = (WIDTH - PADDING * 2 - label_width) / columns
    height = PADDING * 2 + ROW_HEIGHT * (len(diagram.rows) + 1)
    parts: list[str] = []
    top = PADDING
    for index, column in enumerate(diagram.columns):
        x = PADDING + label_width + cell * index
        parts.append(
            _text(x + 8, top + 28, _clip(column, cell - 16, 12), size=12, fill=MUTED, weight="600")
        )
    for row_index, row in enumerate(diagram.rows):
        y = top + ROW_HEIGHT * (row_index + 1)
        parts.append(
            f"<line x1='{PADDING}' y1='{_n(y)}' x2='{WIDTH - PADDING}' y2='{_n(y)}' "
            f"stroke='{RULE}' stroke-width='1'/>"
        )
        parts.append(_text(PADDING + 4, y + 28, _clip(row.label, label_width - 12), weight="600"))
        for cell_index, value in enumerate(row.cells):
            x = PADDING + label_width + cell * cell_index
            parts.append(_text(x + 8, y + 28, _clip(value, cell - 16, 12), size=12))
    return "".join(parts), int(height)


def _chart(diagram: ReportDiagram) -> tuple[str, int]:
    height = 360
    left, right, top, bottom = 72, WIDTH - PADDING, PADDING + 16, height - 52
    points = diagram.series[0].points
    values = [point.value for row in diagram.series for point in row.points]
    low, high = min(values), max(values)
    span = high - low or 1.0
    step = (right - left) / max(1, len(points) - 1)
    parts = [
        f"<line x1='{left}' y1='{top}' x2='{left}' y2='{bottom}' stroke='{RULE}'/>",
        f"<line x1='{left}' y1='{bottom}' x2='{right}' y2='{bottom}' stroke='{RULE}'/>",
        _text(PADDING - 12, top + 5, _clip(_number(high), 60, 11), size=11, fill=MUTED),
        _text(PADDING - 12, bottom, _clip(_number(low), 60, 11), size=11, fill=MUTED),
    ]
    for index, point in enumerate(points):
        x = left + step * index
        parts.append(
            f"<text x='{_n(x)}' y='{bottom + 18}' font-size='11' fill='{MUTED}' "
            f"text-anchor='middle'>{escape(_clip(point.label, step, 11))}</text>"
        )
    for series_index, series in enumerate(diagram.series):
        path = " ".join(
            f"{'M' if index == 0 else 'L'} {_n(left + step * index)} "
            f"{_n(bottom - (point.value - low) / span * (bottom - top))}"
            for index, point in enumerate(series.points)
        )
        dash = SERIES_DASH[series_index % len(SERIES_DASH)]
        attribute = f" stroke-dasharray='{dash}'" if dash else ""
        parts.append(
            f"<path d='{path}' fill='none' stroke='{ACCENT}' stroke-width='2'{attribute}/>"
        )
        parts.append(
            _text(
                left + 8,
                top + 18 * (series_index + 1),
                _clip(series.label, 260, 12),
                size=12,
                fill=MUTED,
            )
        )
    if diagram.unit:
        parts.append(_text(left, height - 16, f"Unit: {diagram.unit}", size=11, fill=MUTED))
    return "".join(parts), height


def _number(value: float) -> str:
    return f"{value:g}"


def _graph(diagram: ReportDiagram) -> tuple[str, int]:
    layers = _layers(diagram)
    usable = WIDTH - PADDING * 2
    box_width = min(240.0, (usable - 40 * (len(layers) - 1)) / len(layers))
    # Spread the layers across the full width so a short chain does not sit in one corner.
    stride = (usable - box_width) / max(1, len(layers) - 1) if len(layers) > 1 else 0.0
    tallest = max(len(layer) for layer in layers)
    height = int(PADDING * 2 + max(1, tallest) * 74)
    centres: dict[str, tuple[float, float]] = {}
    for column, layer in enumerate(layers):
        x = PADDING + column * stride
        for row, node_id in enumerate(layer):
            y = float(PADDING + 32 + row * 74 + (tallest - len(layer)) * 37)
            centres[node_id] = (x + box_width / 2, y)
    parts = [
        "<defs><marker id='ase-arrow' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='6' "
        f"markerHeight='6' orient='auto-start-reverse'><path d='M 0 0 L 10 5 L 0 10 z' "
        f"fill='{MUTED}'/></marker></defs>"
    ]
    for edge in diagram.edges:
        (x1, y1), (x2, y2) = centres[edge.source], centres[edge.target]
        parts.append(
            f"<line x1='{_n(x1)}' y1='{_n(y1)}' x2='{_n(x2)}' y2='{_n(y2)}' stroke='{MUTED}' "
            "stroke-width='1.5' marker-end='url(#ase-arrow)'/>"
        )
        if edge.label:
            parts.append(
                f"<text x='{_n((x1 + x2) / 2)}' y='{_n((y1 + y2) / 2 - 6)}' font-size='11' "
                f"fill='{MUTED}' text-anchor='middle'>"
                f"{escape(_clip(edge.label, box_width, 11))}</text>"
            )
    for node in diagram.nodes:
        x, y = centres[node.id]
        parts.append(
            f"<rect x='{_n(x - box_width / 2)}' y='{_n(y - 24)}' width='{_n(box_width)}' "
            f"height='48' rx='8' fill='#FFFFFF' stroke='{RULE}' stroke-width='1.5'/>"
        )
        parts.append(
            f"<text x='{_n(x)}' y='{_n(y - 2)}' font-size='12' font-weight='600' fill='{INK}' "
            f"text-anchor='middle'>{escape(_clip(node.label, box_width - 16, 12))}</text>"
        )
        if node.detail:
            parts.append(
                f"<text x='{_n(x)}' y='{_n(y + 15)}' font-size='11' fill='{MUTED}' "
                f"text-anchor='middle'>{escape(_clip(node.detail, box_width - 16, 11))}</text>"
            )
    return "".join(parts), height


def _layers(diagram: ReportDiagram) -> list[list[str]]:
    """Longest-path layering, so a causal chain reads left to right and cannot loop."""
    depth = {node.id: 0 for node in diagram.nodes}
    order = [node.id for node in diagram.nodes]
    for _ in range(len(order)):
        changed = False
        for edge in diagram.edges:
            candidate = depth[edge.source] + 1
            if candidate > depth[edge.target] and candidate < len(order):
                depth[edge.target], changed = candidate, True
        if not changed:
            break
    width = max(depth.values()) + 1
    layers: list[list[str]] = [[] for _ in range(width)]
    for node_id in order:
        layers[depth[node_id]].append(node_id)
    return [layer for layer in layers if layer]
