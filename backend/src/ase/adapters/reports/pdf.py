"""Paginated ReportLab export. Every untrusted character is escaped before Paragraph."""

from __future__ import annotations

import io
from html import escape
from pathlib import Path
from typing import cast

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate

from ase.domain.report_documents import BlockKind, ReportDocument

_FONT_NAME = "ASEVera"
_FONT_BOLD = "ASEVeraBold"
_FONT_PATH = Path(reportlab.__file__).parent / "fonts"


def _font_characters() -> set[int]:
    if _FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(_FONT_NAME, str(_FONT_PATH / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont(_FONT_BOLD, str(_FONT_PATH / "VeraBd.ttf")))
    font = cast(TTFont, pdfmetrics.getFont(_FONT_NAME))
    return set(font.face.charToGlyph)


def _safe_text(text: str, characters: set[int]) -> tuple[str, bool]:
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
                "Characters unavailable in the bundled PDF font appear as [U+XXXX] "
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
