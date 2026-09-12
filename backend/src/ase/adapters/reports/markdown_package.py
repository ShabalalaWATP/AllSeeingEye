"""Portable, deterministic Markdown exports with bounded local figures."""

from __future__ import annotations

import io
import zipfile
from uuid import UUID

from ase.adapters.reports.figure_validation import verify_document_figures
from ase.application.reports.publication_markdown import render_document_markdown
from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import BlockKind, ReportDocument, ReportFile

MAX_MARKDOWN_BYTES = 5_000_000
MAX_PACKAGE_INPUT_BYTES = 25_000_000
_ZIP_TIMESTAMP = (2000, 1, 1, 0, 0, 0)


def render_markdown_export(
    document: ReportDocument,
    report_id: UUID,
    version_id: UUID,
    version_number: int,
    *,
    package_figures: bool = True,
) -> ReportFile:
    """Return plain Markdown, or a self-contained ZIP when figures are present."""
    figures = tuple(
        block.figure
        for block in document.blocks
        if block.kind is BlockKind.FIGURE and block.figure is not None
    )
    stem = f"report-{report_id}-v{version_number}"
    if not figures or not package_figures:
        markdown = render_document_markdown(document).encode("utf-8")
        return ReportFile(
            markdown,
            "text/markdown; charset=utf-8",
            f"{stem}.md",
            version_id,
            version_number,
        )

    verified = verify_document_figures(document)
    figure_entries: list[tuple[str, bytes]] = []
    for number, figure in enumerate(figures, start=1):
        extension = "png" if figure.media_type == "image/png" else "jpg"
        figure_entries.append(
            (f"figures/figure-{number}.{extension}", verified[id(figure)].content)
        )
    markdown = render_document_markdown(document, tuple(name for name, _ in figure_entries)).encode(
        "utf-8"
    )
    if len(markdown) > MAX_MARKDOWN_BYTES:
        raise InvalidRequest("The report Markdown exceeds the safe package byte limit.")
    if len(markdown) + sum(len(content) for _, content in figure_entries) > MAX_PACKAGE_INPUT_BYTES:
        raise InvalidRequest("The report exceeds the safe Markdown package byte limit.")

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        _write_entry(archive, "report.md", markdown, compression=zipfile.ZIP_DEFLATED)
        for name, content in figure_entries:
            _write_entry(archive, name, content, compression=zipfile.ZIP_STORED)
    return ReportFile(
        output.getvalue(),
        "application/zip",
        f"{stem}-markdown.zip",
        version_id,
        version_number,
    )


def _write_entry(archive: zipfile.ZipFile, name: str, content: bytes, *, compression: int) -> None:
    entry = zipfile.ZipInfo(name, date_time=_ZIP_TIMESTAMP)
    entry.compress_type = compression
    entry.external_attr = 0o600 << 16
    archive.writestr(entry, content)
