"""Portable Markdown keeps bounded figures beside deterministic report text."""

import io
import zipfile
from dataclasses import replace
from uuid import uuid4

import pytest
from PIL import Image

from ase.adapters.reports.markdown_package import render_markdown_export
from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import (
    BlockKind,
    DocumentBlock,
    DocumentFigure,
    DocumentReference,
    ReportDocument,
)


def _image(format: str) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (12, 8), "navy").save(output, format=format)
    return output.getvalue()


def _document(*figures: DocumentFigure) -> ReportDocument:
    blocks = tuple(
        DocumentBlock(BlockKind.FIGURE, figure.caption, figure=figure) for figure in figures
    )
    reference = DocumentReference(1, "E1", "Source", "Publisher", None, "2026-09-12")
    return ReportDocument("Report", "ASE-1", blocks, references=(reference,))


def _figure(media_type: str = "image/png") -> DocumentFigure:
    format = "PNG" if media_type == "image/png" else "JPEG"
    return DocumentFigure(
        "Observed pattern",
        "Events by location.",
        "Map showing event locations [sample]",
        _image(format),
        media_type,
        12,
        8,
        (1,),
    )


def test_plain_report_remains_an_ordinary_markdown_file() -> None:
    report_id, version_id = uuid4(), uuid4()
    result = render_markdown_export(
        ReportDocument("Report", "ASE-1", (DocumentBlock(BlockKind.TEXT, "Finding"),)),
        report_id,
        version_id,
        3,
    )

    assert result.media_type == "text/markdown; charset=utf-8"
    assert result.filename == f"report-{report_id}-v3.md"
    assert result.content == b"Finding\n"
    assert result.report_version_id == version_id


def test_explicit_plain_markdown_uses_text_alternative_for_figures() -> None:
    report_id, version_id = uuid4(), uuid4()
    result = render_markdown_export(
        _document(_figure()),
        report_id,
        version_id,
        3,
        package_figures=False,
    )

    assert result.media_type == "text/markdown; charset=utf-8"
    assert result.filename == f"report-{report_id}-v3.md"
    markdown = result.content.decode("utf-8")
    assert "Map showing event locations \\[sample\\]" in markdown
    assert "figures/figure-1.png" not in markdown


def test_figures_are_packaged_with_relative_links_and_stable_bytes() -> None:
    report_id, version_id = uuid4(), uuid4()
    document = _document(_figure(), _figure("image/jpeg"))

    first = render_markdown_export(document, report_id, version_id, 4)
    second = render_markdown_export(document, report_id, version_id, 4)

    assert first.content == second.content
    assert first.media_type == "application/zip"
    assert first.filename == f"report-{report_id}-v4-markdown.zip"
    with zipfile.ZipFile(io.BytesIO(first.content)) as archive:
        assert archive.namelist() == [
            "report.md",
            "figures/figure-1.png",
            "figures/figure-2.jpg",
        ]
        assert archive.getinfo("report.md").compress_type == zipfile.ZIP_DEFLATED
        assert archive.getinfo("figures/figure-1.png").compress_type == zipfile.ZIP_STORED
        assert archive.getinfo("figures/figure-2.jpg").compress_type == zipfile.ZIP_STORED
        markdown = archive.read("report.md").decode("utf-8")
        assert "![Map showing event locations \\[sample\\]](figures/figure-1.png)" in markdown
        assert "![Map showing event locations \\[sample\\]](figures/figure-2.jpg)" in markdown
        assert markdown.count("*Events by location.*") == 2
        assert markdown.count("[1](#reference-1)") == 2
        assert Image.open(io.BytesIO(archive.read("figures/figure-1.png"))).format == "PNG"
        assert Image.open(io.BytesIO(archive.read("figures/figure-2.jpg"))).format == "JPEG"


def test_invalid_and_oversized_package_inputs_fail_closed(monkeypatch) -> None:
    bad = replace(_figure(), content=b"not an image")
    with pytest.raises(InvalidRequest, match="invalid figure"):
        render_markdown_export(_document(bad), uuid4(), uuid4(), 1)

    monkeypatch.setattr("ase.adapters.reports.markdown_package.MAX_PACKAGE_INPUT_BYTES", 1)
    with pytest.raises(InvalidRequest, match="package byte limit"):
        render_markdown_export(_document(_figure()), uuid4(), uuid4(), 1)
