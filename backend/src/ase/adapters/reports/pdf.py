"""Paginated ReportLab export. Every untrusted character is escaped before Paragraph."""

from __future__ import annotations

import io
from html import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate

from ase.adapters.reports.font_support import (
    FONT_BOLD as _FONT_BOLD,
)
from ase.adapters.reports.font_support import (
    FONT_REGULAR as _FONT_NAME,
)
from ase.adapters.reports.font_support import (
    font_characters as _font_characters,
)
from ase.domain.report_documents import BlockKind, ReportDocument


def _safe_text(text: str, characters: frozenset[int]) -> tuple[str, bool]:
    """Keep missing glyphs legible and recoverable, rather than silently drawing boxes."""
    escaped_glyphs = False
    output = []
    for character in text:
        if character in "\n\t" or ord(character) in characters:
            output.append(character)
        else:
            escaped_glyphs = True
            output.append(f"[U+{ord(character):04X}]")
    return escape("".join(output), quote=False).replace("\n", "<br/>"), escaped_glyphs


def _styles() -> dict[BlockKind, ParagraphStyle]:
    body = ParagraphStyle("ASEBody", fontName=_FONT_NAME, fontSize=10, leading=15, spaceAfter=7)
    return {
        BlockKind.TEXT: body,
        BlockKind.ANNEX: ParagraphStyle(
            "ASEAnnex",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=14,
            leading=19,
            spaceAfter=8,
            keepWithNext=True,
            pageBreakBefore=True,
        ),
        BlockKind.TITLE: ParagraphStyle(
            "ASETitle",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=22,
            leading=28,
            spaceAfter=15,
            keepWithNext=True,
        ),
        BlockKind.HEADING: ParagraphStyle(
            "ASEHeading",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=14,
            leading=19,
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        ),
        BlockKind.SUBHEADING: ParagraphStyle(
            "ASESubheading",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=10.5,
            leading=15,
            spaceBefore=8,
            keepWithNext=True,
        ),
        BlockKind.METADATA: ParagraphStyle(
            "ASEMetadata",
            parent=body,
            fontSize=8.5,
            leading=13,
            textColor=colors.HexColor("#424b57"),
        ),
        BlockKind.WARNING: ParagraphStyle(
            "ASEWarning",
            parent=body,
            fontName=_FONT_BOLD,
            textColor=colors.HexColor("#853200"),
            backColor=colors.HexColor("#fff0db"),
            borderPadding=8,
            spaceBefore=8,
            spaceAfter=12,
        ),
    }


def render_pdf(document: ReportDocument) -> bytes:
    stream = io.BytesIO()
    characters = _font_characters()
    styles = _styles()
    flowables: list[Flowable] = []
    missing = False
    for block in document.blocks:
        text, replaced = _safe_text(block.text, characters)
        missing = missing or replaced
        flowables.append(Paragraph(text or " ", styles[block.kind]))
    if missing:
        flowables.append(
            Paragraph(
                "This PDF font covers Latin, Greek and Cyrillic text. Unsupported characters "
                "(including Arabic and CJK) and text-direction controls appear as [U+XXXX] "
                "Unicode code points. "
                "The DOCX export retains their original characters.",
                styles[BlockKind.METADATA],
            )
        )

    def footer(canvas: Canvas, doc: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont(_FONT_NAME, 7)
        canvas.setFillColor(colors.HexColor("#424b57"))
        canvas.drawString(48, 27, document.reference)
        canvas.drawRightString(A4[0] - 48, 27, f"Page {doc.page}")
        canvas.restoreState()

    pdf = SimpleDocTemplate(
        stream,
        pagesize=A4,
        leftMargin=48,
        rightMargin=48,
        topMargin=44,
        bottomMargin=48,
        title=document.title,
        author="The All Seeing Eye",
    )
    pdf.build(flowables, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
