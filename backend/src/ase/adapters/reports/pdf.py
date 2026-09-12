"""Professional paginated PDF rendering for the bounded report document contract."""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate

from ase.adapters.reports.document_validation import validate_document_content
from ase.adapters.reports.figure_validation import verify_document_figures
from ase.adapters.reports.font_support import FONT_BOLD as _FONT_BOLD
from ase.adapters.reports.font_support import FONT_REGULAR as _FONT_NAME
from ase.adapters.reports.font_support import cjk_font
from ase.adapters.reports.font_support import font_characters as _font_characters
from ase.adapters.reports.pdf_content import build_flowables
from ase.domain.report_documents import BlockKind, ReportDocument


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
            textColor=colors.HexColor("#101820"),
            spaceAfter=15,
            keepWithNext=True,
        ),
        BlockKind.HEADING: ParagraphStyle(
            "ASEHeading",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=14,
            leading=19,
            textColor=colors.HexColor("#101820"),
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
            textColor=colors.HexColor("#101820"),
            spaceBefore=8,
            keepWithNext=True,
        ),
        BlockKind.METADATA: ParagraphStyle(
            "ASEMetadata",
            parent=body,
            fontSize=8.5,
            leading=13,
            textColor=colors.HexColor("#59636E"),
        ),
        BlockKind.WARNING: ParagraphStyle(
            "ASEWarning",
            parent=body,
            fontName=_FONT_BOLD,
            textColor=colors.HexColor("#853200"),
            backColor=colors.HexColor("#FFF0DB"),
            borderPadding=8,
            spaceBefore=8,
            spaceAfter=12,
        ),
        BlockKind.REFERENCE: ParagraphStyle(
            "ASEReference",
            parent=body,
            fontSize=8.5,
            leading=12,
            spaceAfter=6,
        ),
    }


class _ReportDocTemplate(SimpleDocTemplate):
    """Add a useful PDF outline without allowing report text to become markup."""

    _outline_index = 0
    _outline_level = -1

    def afterFlowable(self, flowable: Flowable) -> None:  # noqa: N802
        if not isinstance(flowable, Paragraph):
            return
        levels = {"ASETitle": 0, "ASEHeading": 1, "ASEAnnex": 1, "ASESubheading": 2}
        level = levels.get(flowable.style.name)
        if level is None:
            return
        level = min(level, self._outline_level + 1)
        self._outline_level = level
        self._outline_index += 1
        key = f"section-{self._outline_index}"
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(flowable.getPlainText(), key, level=level, closed=False)


def render_pdf(document: ReportDocument) -> bytes:
    validate_document_content(document)
    stream = io.BytesIO()
    figures = verify_document_figures(document)
    characters = _font_characters()
    styles = _styles()
    selected_font = _FONT_NAME
    if document.language in {"zh", "zh-Hans", "zh-Hant"}:
        selected_font, characters = cjk_font(document.language)
        for style in styles.values():
            style.fontName = selected_font
            style.wordWrap = "CJK"
    flowables, missing = build_flowables(document, styles, characters, figures)
    if missing:
        flowables.append(
            Paragraph(
                "Unsupported characters and text-direction controls appear as [U+XXXX] Unicode "
                "code points. The DOCX export retains their original characters.",
                styles[BlockKind.METADATA],
            )
        )

    def footer(canvas: Canvas, doc: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont(selected_font, 7)
        canvas.setFillColor(colors.HexColor("#59636E"))
        canvas.drawString(48, 27, document.reference)
        canvas.drawRightString(A4[0] - 48, 27, f"Page {doc.page}")
        canvas.restoreState()

    pdf = _ReportDocTemplate(
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
