"""Renderer boundaries reject unsafe markup, forged metadata and expanded image limits."""

import io
from dataclasses import replace

import pytest
from PIL import Image

from ase.adapters.reports import diagram_validation, figure_validation
from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import (
    BlockKind,
    DocumentBlock,
    DocumentDiagram,
    DocumentFigure,
    ReportDocument,
)


def diagram_document(svg):
    drawing = DocumentDiagram("Drawing", "Caption", "Description", svg)
    return ReportDocument("Report", "REF", (DocumentBlock(BlockKind.DIAGRAM, "", diagram=drawing),))


@pytest.mark.parametrize(
    "svg,reason",
    [
        ('<svg width="2">< invalid </svg>', "markup"),
        ('<svg width="2" onclick="run()"></svg>', "attribute"),
        ('<svg width="2" fill="javascript:run()"></svg>', "value"),
        ('<svg width="2"><script></script></svg>', "element"),
    ],
)
def test_renderer_rejects_unsupported_svg(svg, reason):
    with pytest.raises(InvalidRequest, match=reason):
        diagram_validation.verify_document_diagrams(diagram_document(svg))


def test_renderer_enforces_its_own_diagram_size_limit(monkeypatch):
    document = diagram_document('<svg width="2"></svg>')
    monkeypatch.setattr(diagram_validation, "MAX_DIAGRAM_CHARACTERS", 10)
    with pytest.raises(InvalidRequest, match="size limit"):
        diagram_validation.verify_document_diagrams(document)


def figure(mode="RGB", image_format="PNG"):
    output = io.BytesIO()
    Image.new(mode, (3, 2)).save(output, format=image_format)
    return DocumentFigure(
        "Image",
        "Caption",
        "Description",
        output.getvalue(),
        "image/png" if image_format == "PNG" else "image/jpeg",
        3,
        2,
    )


def figure_document(image):
    return ReportDocument("Report", "REF", (DocumentBlock(BlockKind.FIGURE, "", figure=image),))


@pytest.mark.parametrize("change", [{"width_px": 4}, {"media_type": "image/jpeg"}])
def test_figure_metadata_must_match_decoded_bytes(change):
    with pytest.raises(InvalidRequest, match="metadata"):
        figure_validation.verify_figure(replace(figure(), **change))


def test_decoded_figure_pixel_cap_is_enforced(monkeypatch):
    monkeypatch.setattr(figure_validation, "MAX_FIGURE_PIXELS", 5)
    with pytest.raises(InvalidRequest, match="pixel limit"):
        figure_validation.verify_figure(figure())


@pytest.mark.parametrize("mode,image_format", [("RGBA", "PNG"), ("RGB", "JPEG")])
def test_supported_image_modes_are_normalised(mode, image_format):
    verified = figure_validation.verify_figure(figure(mode, image_format))
    with Image.open(io.BytesIO(verified.content)) as decoded:
        assert decoded.format == image_format
        assert decoded.size == (3, 2)


def test_document_caps_apply_after_decoding_too(monkeypatch):
    image = figure()
    expanded = figure_validation.VerifiedFigure(b"x" * 100, 3, 2)
    monkeypatch.setattr(figure_validation, "verify_figure", lambda _: expanded)
    monkeypatch.setattr(figure_validation, "MAX_DOCUMENT_FIGURE_BYTES", 90)
    with pytest.raises(InvalidRequest, match="byte limit"):
        figure_validation.verify_document_figures(figure_document(image))
    monkeypatch.setattr(figure_validation, "MAX_DOCUMENT_FIGURE_BYTES", 1000)
    monkeypatch.setattr(figure_validation, "MAX_DOCUMENT_FIGURE_PIXELS", 5)
    with pytest.raises(InvalidRequest, match="pixel limit"):
        figure_validation.verify_document_figures(figure_document(image))
