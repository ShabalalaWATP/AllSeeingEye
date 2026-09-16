"""Renderer-side allowlist for application-drawn diagrams, checked before embedding.

The application generates this markup itself from validated data, so this check should
never fire. It exists so that a future change to the drawing code cannot quietly put a
script, an external reference or an event handler into an exported document.
"""

from __future__ import annotations

import re

from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import BlockKind, ReportDocument

MAX_DIAGRAM_CHARACTERS = 60_000
_TAGS = frozenset(
    {
        "svg",
        "title",
        "desc",
        "defs",
        "marker",
        "g",
        "rect",
        "circle",
        "line",
        "path",
        "text",
        "tspan",
    }
)
_ATTRIBUTES = frozenset(
    {
        "aria-label",
        "cx",
        "cy",
        "d",
        "fill",
        "font-family",
        "font-size",
        "font-weight",
        "height",
        "id",
        "markerheight",
        "markerwidth",
        "marker-end",
        "marker-start",
        "orient",
        "r",
        "refx",
        "refy",
        "role",
        "rx",
        "ry",
        "stroke",
        "stroke-dasharray",
        "stroke-width",
        "text-anchor",
        "viewbox",
        "width",
        "x",
        "x1",
        "x2",
        "xmlns",
        "y",
        "y1",
        "y2",
    }
)
_ELEMENT = re.compile(r"<\s*(/?)([A-Za-z][\w:-]*)((?:[^<>\"']|\"[^\"]*\"|'[^']*')*)/?\s*>")
_ATTRIBUTE = re.compile(r"([A-Za-z][\w:-]*)\s*=\s*(?:\"[^\"]*\"|'[^']*')")


def verify_document_diagrams(document: ReportDocument) -> None:
    for block in document.blocks:
        if block.kind is not BlockKind.DIAGRAM or block.diagram is None:
            continue
        _verify(block.diagram.svg)


def _verify(svg: str) -> None:
    if len(svg) > MAX_DIAGRAM_CHARACTERS:
        raise InvalidRequest("This report exceeds the diagram rendering size limit.")
    stripped = _ELEMENT.sub("", svg)
    if "<" in stripped or ">" in stripped.replace("&gt;", ""):
        raise InvalidRequest("The generated diagram contains markup that cannot be rendered.")
    for _closing, tag, attributes in _ELEMENT.findall(svg):
        if tag.lower() not in _TAGS:
            raise InvalidRequest("The generated diagram contains an unsupported element.")
        for name in _ATTRIBUTE.findall(attributes):
            if name.lower() not in _ATTRIBUTES:
                raise InvalidRequest("The generated diagram contains an unsupported attribute.")
        if re.search(r"(?i)(javascript:|data:|&#|<!)", attributes):
            raise InvalidRequest("The generated diagram contains an unsupported value.")
