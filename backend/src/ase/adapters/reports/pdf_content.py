"""Safe ReportLab flowables for the report's semantic content elements."""

from __future__ import annotations

import io
import re
from collections.abc import Sequence
from html import escape
from typing import Any, cast
from urllib.parse import urlsplit

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    CondPageBreak,
    Flowable,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    LongTable,
    Paragraph,
    TableStyle,
)

from ase.adapters.reports.figure_validation import VerifiedFigure
from ase.adapters.reports.pdf_styles import ACCENT, PAGE_WIDTH, Rule
from ase.domain.report_documents import (
    BlockKind,
    DocumentBlock,
    DocumentFigure,
    DocumentInline,
    DocumentReference,
    DocumentTable,
    ReportDocument,
)

_CITATION_NUMBER = re.compile(r"\d+")
_PAGE_WIDTH = PAGE_WIDTH


def safe_text(text: str, characters: frozenset[int]) -> tuple[str, bool]:
    """Keep missing glyphs recoverable instead of silently drawing replacement boxes."""
    escaped_glyphs = False
    output = []
    for character in text:
        if character in "\n\t" or ord(character) in characters:
            output.append(character)
        else:
            escaped_glyphs = True
            output.append(f"[U+{ord(character):04X}]")
    return escape("".join(output), quote=False).replace("\n", "<br/>"), escaped_glyphs


def _safe_url(value: str | None) -> str | None:
    if not value or len(value) > 2_048 or any(ord(char) < 32 for char in value):
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username is not None or parsed.password is not None:
        return None
    return value


def _citation_markup(inline: DocumentInline, characters: frozenset[int]) -> tuple[str, bool]:
    matches = tuple(_CITATION_NUMBER.finditer(inline.text))
    if tuple(int(match.group()) for match in matches) != inline.citation_numbers:
        return safe_text(inline.text, characters)
    numbers = iter(inline.citation_numbers)
    parts: list[str] = []
    missing = False
    cursor = 0
    for match in matches:
        try:
            number = next(numbers)
        except StopIteration:
            break
        prefix, replaced = safe_text(inline.text[cursor : match.start()], characters)
        missing = missing or replaced
        parts.append(prefix)
        parts.append(f'<link href="#reference-{number}">{match.group()}</link>')
        cursor = match.end()
    suffix, replaced = safe_text(inline.text[cursor:], characters)
    parts.append(suffix)
    return "".join(parts), missing or replaced


def inline_markup(
    text: str, inlines: tuple[DocumentInline, ...], characters: frozenset[int]
) -> tuple[str, bool]:
    if not inlines:
        return safe_text(text, characters)
    output: list[str] = []
    missing = False
    for inline in inlines:
        if inline.citation_numbers:
            value, replaced = _citation_markup(inline, characters)
        else:
            value, replaced = safe_text(inline.text, characters)
        output.append(value)
        missing = missing or replaced
    return "".join(output), missing


def _reference_markup(
    reference: DocumentReference, text: str, characters: frozenset[int]
) -> tuple[str, bool]:
    anchor = f'<a name="reference-{reference.number}"/>'
    urls = list(
        dict.fromkeys(
            url
            for candidate in (reference.url, reference.archive_url)
            if (url := _safe_url(candidate)) is not None
        )
    )
    if not urls:
        value, replaced = safe_text(text, characters)
        return anchor + value, replaced
    parts = [anchor]
    missing = False
    cursor = 0
    while urls:
        matches = [(text.find(url, cursor), -len(url), url) for url in urls]
        matches = [match for match in matches if match[0] >= 0]
        if not matches:
            break
        start, _, url = min(matches)
        prefix, replaced = safe_text(text[cursor:start], characters)
        parts.append(prefix)
        parts.append(
            f'<link href="{escape(url, quote=True)}" color="#16748A">'
            f"{escape(url, quote=False)}</link>"
        )
        missing = missing or replaced
        cursor = start + len(url)
        urls.remove(url)
    suffix, replaced = safe_text(text[cursor:], characters)
    parts.append(suffix)
    return "".join(parts), missing or replaced


def _column_widths(table: DocumentTable) -> list[float]:
    """Give each column room in proportion to its content, within readable bounds.

    Equal thirds leave date columns half empty while prose columns wrap to shreds, so
    the share is taken from the longest cell in each column and then clamped.
    """
    longest = [
        max(
            [len(column), *(len(row[index].text) for row in table.rows)],
            default=1,
        )
        for index, column in enumerate(table.columns)
    ]
    # A long cell wraps, so its width should grow far more slowly than its length.
    weights = [max(6.0, min(float(value), 90.0)) ** 0.62 for value in longest]
    total = sum(weights) or 1.0
    minimum = min(_PAGE_WIDTH / len(table.columns) * 0.42, 54.0)
    widths = [max(minimum, _PAGE_WIDTH * weight / total) for weight in weights]
    excess = sum(widths) / _PAGE_WIDTH
    return [width / excess for width in widths]


def _table_flowables(
    table: DocumentTable,
    styles: dict[BlockKind, ParagraphStyle],
    characters: frozenset[int],
) -> tuple[list[Flowable], bool]:
    title, missing = safe_text(table.title, characters)
    widths = _column_widths(table)
    # A long table must not be pushed whole onto the next page by its heading's
    # keep-with-next, which leaves a near-empty page. The title keeps its own space
    # instead, and the repeated header row carries the column names onto every page.
    title_style = ParagraphStyle(
        "ASETableTitle", parent=styles[BlockKind.SUBHEADING], keepWithNext=False
    )
    cell_style = ParagraphStyle(
        "ASETableCell", parent=styles[BlockKind.TEXT], fontSize=8.2, leading=11.4, spaceAfter=0
    )
    header_style = ParagraphStyle(
        "ASETableHeader",
        parent=cell_style,
        fontName=styles[BlockKind.SUBHEADING].fontName,
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#3E3932"),
    )
    header: list[Paragraph] = []
    for column in table.columns:
        value, replaced = safe_text(column, characters)
        header.append(Paragraph(value or " ", header_style))
        missing = missing or replaced
    data: list[list[Paragraph]] = [header]
    for row in table.rows:
        rendered: list[Paragraph] = []
        for cell in row:
            value, replaced = inline_markup(cell.text, cell.inlines, characters)
            rendered.append(Paragraph(value or " ", cell_style))
            missing = missing or replaced
        data.append(rendered)
    native = LongTable(
        data,
        colWidths=widths,
        repeatRows=1,
        hAlign="LEFT",
        splitByRow=1,
    )
    # Horizontal rules only: vertical grid lines fight with wrapped prose cells.
    native.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1ECE1")),
                ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.HexColor("#B9B1A2")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#B9B1A2")),
                ("LINEBELOW", (0, 1), (-1, -1), 0.35, colors.HexColor("#E0D9CC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAF8F3")]),
            ]
        )
    )
    result: list[Flowable] = [
        CondPageBreak(78),
        Paragraph(title, title_style),
        native,
    ]
    if table.caption:
        caption, replaced = safe_text(table.caption, characters)
        result.append(Paragraph(caption, styles[BlockKind.METADATA]))
        missing = missing or replaced
    return result, missing


def _figure_flowables(
    figure: DocumentFigure,
    verified: VerifiedFigure,
    styles: dict[BlockKind, ParagraphStyle],
    characters: frozenset[int],
) -> tuple[list[Flowable], bool]:
    max_width, max_height = _PAGE_WIDTH, 6.3 * inch
    scale = min(max_width / verified.width, max_height / verified.height)
    image = Image(
        io.BytesIO(verified.content),
        width=verified.width * scale,
        height=verified.height * scale,
    )
    image.hAlign = "CENTER"
    caption_text = f"{figure.title}. {figure.caption}"
    if figure.citation_numbers:
        citation = f" [{', '.join(str(number) for number in figure.citation_numbers)}]"
        caption, missing = inline_markup(
            caption_text + citation,
            (
                DocumentInline(caption_text),
                DocumentInline(citation, "ltr", figure.citation_numbers),
            ),
            characters,
        )
    else:
        caption, missing = safe_text(caption_text, characters)
    return [KeepTogether([image, Paragraph(caption, styles[BlockKind.METADATA])])], missing


def build_flowables(
    document: ReportDocument,
    styles: dict[BlockKind, ParagraphStyle],
    characters: frozenset[int],
    figures: dict[int, VerifiedFigure],
    *,
    blocks: Sequence[DocumentBlock] | None = None,
) -> tuple[list[Flowable], bool]:
    """Render the document's blocks, or the given subset when a masthead took the rest."""
    flowables: list[Flowable] = []
    missing = False
    reference_index = 0
    section = 0
    for block in document.blocks if blocks is None else blocks:
        if block.kind is BlockKind.TABLE and block.table:
            added, replaced = _table_flowables(block.table, styles, characters)
            flowables.extend(added)
            missing = missing or replaced
            continue
        if block.kind is BlockKind.FIGURE and block.figure:
            added, replaced = _figure_flowables(
                block.figure, figures[id(block.figure)], styles, characters
            )
            flowables.extend(added)
            missing = missing or replaced
            continue
        if block.kind is BlockKind.LIST:
            items = []
            for item in block.items:
                value, replaced = inline_markup(item.text, item.inlines, characters)
                items.append(
                    ListItem(
                        Paragraph(value or " ", styles[BlockKind.TEXT]),
                        leftIndent=16,
                        spaceBefore=1,
                    )
                )
                missing = missing or replaced
            flowables.append(
                ListFlowable(
                    cast("list[Any]", items),
                    bulletType="1" if block.ordered else "bullet",
                    bulletFontSize=8,
                    bulletOffsetY=-1,
                    leftIndent=16,
                    bulletDedent=10,
                    spaceBefore=2,
                    spaceAfter=5,
                )
            )
            continue
        if block.kind is BlockKind.REFERENCE and reference_index < len(document.references):
            text, replaced = _reference_markup(
                document.references[reference_index], block.text, characters
            )
            reference_index += 1
        else:
            text, replaced = inline_markup(block.text, block.inlines, characters)
        missing = missing or replaced
        if block.kind in {BlockKind.HEADING, BlockKind.ANNEX}:
            # Section headings anchor the page in the export exactly as they do on
            # screen: an accent number, the heading, then a rule across the measure.
            section += 1
            number = f'<font color="#{ACCENT.hexval()[2:]}">{section:02d}</font>&nbsp;&nbsp;'
            flowables.append(Paragraph(number + (text or " "), styles[block.kind]))
            rule = Rule(_PAGE_WIDTH, 1.1, accent=0, space_below=6)
            rule.keepWithNext = 1
            flowables.append(rule)
            continue
        flowables.append(Paragraph(text or " ", styles[block.kind]))
    return flowables, missing
