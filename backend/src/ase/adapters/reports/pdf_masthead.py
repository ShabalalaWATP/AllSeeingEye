"""The opening identity block of the exported report, matching the on-screen paper."""

from __future__ import annotations

from collections.abc import Callable

from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Flowable, KeepTogether, Paragraph

from ase.adapters.reports.pdf_styles import ACCENT, PAGE_WIDTH, Rule
from ase.domain.report_documents import BlockKind, DocumentBlock


def masthead_flowables(
    head: list[DocumentBlock],
    styles: dict[BlockKind, ParagraphStyle],
    render: Callable[[DocumentBlock], str],
) -> list[Flowable]:
    """Build the eyebrow, title, colophon and closing rule from the leading blocks."""
    eyebrow = ParagraphStyle(
        "ASEEyebrow",
        parent=styles[BlockKind.METADATA],
        fontName=styles[BlockKind.TITLE].fontName,
        fontSize=7,
        leading=10,
        textColor=ACCENT,
        spaceAfter=2,
    )
    flowables: list[Flowable] = [Paragraph("INTELLIGENCE PRODUCT", eyebrow)]
    flowables.extend(Paragraph(render(block) or " ", styles[block.kind]) for block in head)
    flowables.append(Rule(PAGE_WIDTH, 1.1, accent=54, space_below=4))
    return [KeepTogether(flowables)]
