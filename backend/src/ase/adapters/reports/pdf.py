"""Professional paginated PDF rendering for the bounded report document contract."""

from __future__ import annotations

import io
from typing import Any, cast

from reportlab.lib.pagesizes import A4
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate

from ase.adapters.reports.document_sections import leading_identity
from ase.adapters.reports.document_validation import validate_document_content
from ase.adapters.reports.figure_validation import verify_document_figures
from ase.adapters.reports.font_support import FONT_REGULAR as _FONT_NAME
from ase.adapters.reports.font_support import cjk_font
from ase.adapters.reports.font_support import font_characters as _font_characters
from ase.adapters.reports.pdf_content import build_flowables, inline_markup
from ase.adapters.reports.pdf_masthead import masthead_flowables
from ase.adapters.reports.pdf_styles import (
    BOTTOM_MARGIN,
    LEFT_MARGIN,
    RIGHT_MARGIN,
    TOP_MARGIN,
    NumberedCanvas,
    page_furniture,
    styles,
)
from ase.domain.report_documents import BlockKind, ReportDocument

_OUTLINE_LEVELS = {"ASETitle": 0, "ASEHeading": 1, "ASEAnnex": 1, "ASESubheading": 2}


class _ReportDocTemplate(SimpleDocTemplate):
    """Add a useful PDF outline without allowing report text to become markup."""

    _outline_index = 0
    _outline_level = -1

    def afterFlowable(self, flowable: Flowable) -> None:  # noqa: N802
        if not isinstance(flowable, Paragraph):
            return
        level = _OUTLINE_LEVELS.get(flowable.style.name)
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
    style_map = styles()
    selected_font = _FONT_NAME
    if document.language in {"zh", "zh-Hans", "zh-Hant"}:
        selected_font, characters = cjk_font(document.language)
        for style in style_map.values():
            style.fontName = selected_font
            style.wordWrap = "CJK"

    head, remaining = leading_identity(document)
    flowables = masthead_flowables(
        head,
        style_map,
        lambda block: inline_markup(block.text, block.inlines, characters)[0],
    )
    body, missing = build_flowables(document, style_map, characters, figures, blocks=remaining)
    flowables.extend(body)
    if missing:
        flowables.append(
            Paragraph(
                "Unsupported characters and text-direction controls appear as [U+XXXX] Unicode "
                "code points. The DOCX export retains their original characters.",
                style_map[BlockKind.METADATA],
            )
        )

    pdf = _ReportDocTemplate(
        stream,
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title=document.title,
        author="The All Seeing Eye",
        subject=document.reference,
        lang=document.language,
        displayDocTitle=1,
        # Identical input must produce identical bytes so export hashes and version
        # comparisons stay stable; this pins the creation date and document id.
        invariant=1,
    )
    furniture = page_furniture(document, selected_font)
    canvas_class = type("_ASECanvas", (NumberedCanvas,), {"page_font": selected_font})
    pdf.build(
        flowables,
        onFirstPage=furniture,
        onLaterPages=furniture,
        canvasmaker=cast("Any", canvas_class),
    )
    return stream.getvalue()
