"""Safe ReportLab flowables for the report's semantic content elements."""

from __future__ import annotations

import io
import re
from html import escape
from typing import Any, cast
from urllib.parse import urlsplit

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
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
from ase.domain.report_documents import (
    BlockKind,
    DocumentFigure,
    DocumentInline,
    DocumentReference,
    DocumentTable,
    ReportDocument,
)

_CITATION_NUMBER = re.compile(r"\d+")
_PAGE_WIDTH = A4[0] - 96


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


def _inline_markup(
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


def _table_flowables(
    table: DocumentTable,
    styles: dict[BlockKind, ParagraphStyle],
    characters: frozenset[int],
) -> tuple[list[Flowable], bool]:
    title, missing = safe_text(table.title, characters)
    column_width = _PAGE_WIDTH / len(table.columns)
    cell_style = ParagraphStyle(
        "ASETableCell", parent=styles[BlockKind.TEXT], fontSize=8, leading=10, spaceAfter=0
    )
    header_style = ParagraphStyle(
        "ASETableHeader",
        parent=cell_style,
        fontName=styles[BlockKind.SUBHEADING].fontName,
        textColor=colors.HexColor("#FFFFFF"),
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
            value, replaced = _inline_markup(cell.text, cell.inlines, characters)
            rendered.append(Paragraph(value or " ", cell_style))
            missing = missing or replaced
        data.append(rendered)
    native = LongTable(
        data,
        colWidths=[column_width] * len(table.columns),
        repeatRows=1,
        hAlign="LEFT",
        splitByRow=1,
    )
    native.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#183746")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#BAC2C9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F7")]),
            ]
        )
    )
    result: list[Flowable] = [Paragraph(title, styles[BlockKind.SUBHEADING]), native]
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
        caption, missing = _inline_markup(
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
) -> tuple[list[Flowable], bool]:
    flowables: list[Flowable] = []
    missing = False
    reference_index = 0
    for block in document.blocks:
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
        if block.kind is BlockKind.DIAGRAM and block.diagram:
            # This renderer draws no vectors. The text alternative carries the content
            # and the equivalent table follows immediately, so nothing is lost.
            caption = f"{block.diagram.title}. {block.diagram.alt_text}"
            text, replaced = safe_text(caption, characters)
            flowables.append(Paragraph(text or " ", styles[BlockKind.METADATA]))
            missing = missing or replaced
            continue
        if block.kind is BlockKind.LIST:
            items = []
            for item in block.items:
                value, replaced = _inline_markup(item.text, item.inlines, characters)
                items.append(ListItem(Paragraph(value or " ", styles[BlockKind.TEXT])))
                missing = missing or replaced
            flowables.append(
                ListFlowable(
                    cast("list[Any]", items),
                    bulletType="1" if block.ordered else "bullet",
                )
            )
            continue
        if block.kind is BlockKind.REFERENCE and reference_index < len(document.references):
            text, replaced = _reference_markup(
                document.references[reference_index], block.text, characters
            )
            reference_index += 1
        else:
            text, replaced = _inline_markup(block.text, block.inlines, characters)
        missing = missing or replaced
        flowables.append(Paragraph(text or " ", styles[block.kind]))
    return flowables, missing
