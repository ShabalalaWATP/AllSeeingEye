"""Typography scale and page furniture for the paginated report PDF."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, SimpleDocTemplate

from ase.adapters.reports.font_support import FONT_BOLD as _FONT_BOLD
from ase.adapters.reports.font_support import FONT_REGULAR as _FONT_NAME
from ase.domain.report_documents import BlockKind, ReportDocument

INK = colors.HexColor("#17140F")
INK_SOFT = colors.HexColor("#635D53")
ACCENT = colors.HexColor("#97370F")
RULE = colors.HexColor("#D9D2C5")
RULE_SOFT = colors.HexColor("#E8E1D4")
BAND = colors.HexColor("#F1ECE1")
CAUTION_INK = colors.HexColor("#6B3F10")
CAUTION_BAND = colors.HexColor("#FDF4E2")

LEFT_MARGIN = 54
RIGHT_MARGIN = 54
TOP_MARGIN = 62
BOTTOM_MARGIN = 58
PAGE_WIDTH = A4[0] - LEFT_MARGIN - RIGHT_MARGIN


def styles() -> dict[BlockKind, ParagraphStyle]:
    """One scale for the whole document, so every level is distinguishable."""
    body = ParagraphStyle(
        "ASEBody",
        fontName=_FONT_NAME,
        fontSize=9.7,
        leading=14.4,
        spaceAfter=7,
        textColor=INK,
    )
    return {
        BlockKind.TEXT: body,
        BlockKind.TITLE: ParagraphStyle(
            "ASETitle",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=21,
            leading=25,
            textColor=INK,
            spaceBefore=4,
            spaceAfter=8,
            keepWithNext=True,
        ),
        BlockKind.HEADING: ParagraphStyle(
            "ASEHeading",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=13.5,
            leading=17,
            textColor=INK,
            spaceBefore=20,
            spaceAfter=3,
            keepWithNext=True,
        ),
        BlockKind.ANNEX: ParagraphStyle(
            "ASEAnnex",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=13.5,
            leading=17,
            textColor=INK,
            spaceBefore=0,
            spaceAfter=3,
            keepWithNext=True,
            pageBreakBefore=True,
        ),
        BlockKind.SUBHEADING: ParagraphStyle(
            "ASESubheading",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=9.9,
            leading=14,
            textColor=ACCENT,
            spaceBefore=13,
            spaceAfter=1,
            keepWithNext=True,
        ),
        BlockKind.METADATA: ParagraphStyle(
            "ASEMetadata",
            parent=body,
            fontSize=8,
            leading=12,
            textColor=INK_SOFT,
            spaceAfter=3,
        ),
        BlockKind.WARNING: ParagraphStyle(
            "ASEWarning",
            parent=body,
            fontName=_FONT_BOLD,
            fontSize=9.2,
            leading=13.5,
            textColor=CAUTION_INK,
            backColor=CAUTION_BAND,
            borderColor=colors.HexColor("#CF9736"),
            borderWidth=0.6,
            borderPadding=8,
            spaceBefore=9,
            spaceAfter=11,
        ),
        BlockKind.REFERENCE: ParagraphStyle(
            "ASEReference",
            parent=body,
            fontSize=8.2,
            leading=11.8,
            leftIndent=18,
            firstLineIndent=-18,
            spaceAfter=6,
        ),
    }


class Rule(Flowable):
    """A horizontal rule with an optional short accent run at its start."""

    def __init__(
        self, width: float, thickness: float = 0.6, accent: float = 0.0, space_below: float = 0.0
    ) -> None:
        super().__init__()
        self.width = width
        self.height = thickness + space_below
        self._thickness = thickness
        self._accent = accent
        self._space = space_below

    def draw(self) -> None:
        canvas = self.canv
        canvas.setLineWidth(self._thickness)
        canvas.setStrokeColor(RULE if self._accent else INK)
        canvas.line(self._accent, self._space, self.width, self._space)
        if self._accent:
            canvas.setStrokeColor(ACCENT)
            canvas.setLineWidth(self._thickness * 2)
            canvas.line(0, self._space, self._accent, self._space)


HEAD_BASELINE = A4[1] - 40
FOOT_RULE = BOTTOM_MARGIN - 18
FOOT_BASELINE = BOTTOM_MARGIN - 30


def page_furniture(
    document: ReportDocument, font: str
) -> Callable[[Canvas, SimpleDocTemplate], None]:
    """Draw the running head and the footer rule; the page count is added on save."""
    title = document.title if len(document.title) <= 78 else document.title[:75] + "..."

    def draw(canvas: Canvas, doc: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont(font, 7)
        canvas.setFillColor(INK_SOFT)
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        if doc.page > 1:
            canvas.drawString(LEFT_MARGIN, HEAD_BASELINE, title)
            canvas.drawRightString(A4[0] - RIGHT_MARGIN, HEAD_BASELINE, document.reference)
            canvas.line(LEFT_MARGIN, HEAD_BASELINE - 6, A4[0] - RIGHT_MARGIN, HEAD_BASELINE - 6)
        canvas.line(LEFT_MARGIN, FOOT_RULE, A4[0] - RIGHT_MARGIN, FOOT_RULE)
        canvas.drawString(LEFT_MARGIN, FOOT_BASELINE, document.reference)
        canvas.restoreState()

    return draw


class NumberedCanvas(Canvas):
    """Write "Page n of m" once the total is known, without a second render pass."""

    page_font = _FONT_NAME

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._pages: list[dict[str, Any]] = []

    def showPage(self) -> None:  # noqa: N802
        self._pages.append(dict(self.__dict__))
        # ReportLab's own page reset; deferring the real showPage is how the total
        # page count becomes available before anything is written.
        start_page = cast("Callable[[], None]", getattr(self, "_startPage"))  # noqa: B009
        start_page()

    def save(self) -> None:
        total = len(self._pages)
        for state in self._pages:
            self.__dict__.update(state)
            number = cast(int, self.__dict__.get("_pageNumber", 0))
            self.saveState()
            self.setFont(self.page_font, 7)
            self.setFillColor(INK_SOFT)
            self.drawRightString(
                A4[0] - RIGHT_MARGIN,
                FOOT_BASELINE,
                f"Page {number} of {total}",
            )
            self.restoreState()
            super().showPage()
        super().save()
