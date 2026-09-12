"""Decode and bound trusted-local report figure bytes before document embedding."""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image as PillowImage

from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import DocumentFigure, ReportDocument

MAX_FIGURE_PIXELS = 40_000_000
MAX_DOCUMENT_FIGURE_PIXELS = 80_000_000
MAX_DOCUMENT_FIGURE_BYTES = 20_000_000


@dataclass(frozen=True, slots=True)
class VerifiedFigure:
    content: bytes
    width: int
    height: int


def verify_figure(figure: DocumentFigure) -> VerifiedFigure:
    expected = "PNG" if figure.media_type == "image/png" else "JPEG"
    try:
        with PillowImage.open(io.BytesIO(figure.content)) as image:
            if image.format != expected or image.size != (figure.width_px, figure.height_px):
                raise InvalidRequest("The report figure metadata does not match its image.")
            if image.width * image.height > MAX_FIGURE_PIXELS:
                raise InvalidRequest("The report figure exceeds the safe pixel limit.")
            image.load()
            normalised = image.convert(
                "RGBA" if expected == "PNG" and "A" in image.getbands() else "RGB"
            )
            output = io.BytesIO()
            normalised.save(output, format=expected)
    except InvalidRequest:
        raise
    except Exception as error:
        raise InvalidRequest("The report contains an invalid figure.") from error
    return VerifiedFigure(output.getvalue(), figure.width_px, figure.height_px)


def verify_document_figures(document: ReportDocument) -> dict[int, VerifiedFigure]:
    figures = tuple(block.figure for block in document.blocks if block.figure is not None)
    if sum(len(figure.content) for figure in figures) > MAX_DOCUMENT_FIGURE_BYTES:
        raise InvalidRequest("The report figures exceed the safe document byte limit.")
    decoded = tuple((figure, verify_figure(figure)) for figure in figures)
    if sum(len(item.content) for _, item in decoded) > MAX_DOCUMENT_FIGURE_BYTES:
        raise InvalidRequest("The report figures exceed the safe document byte limit.")
    if sum(item.width * item.height for _, item in decoded) > MAX_DOCUMENT_FIGURE_PIXELS:
        raise InvalidRequest("The report figures exceed the safe document pixel limit.")
    return {id(figure): item for figure, item in decoded}
