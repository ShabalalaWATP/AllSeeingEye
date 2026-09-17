"""Word styles, page furniture and the opening identity block for the DOCX export."""

from __future__ import annotations

from collections.abc import Callable

from docx.document import Document as WordDocument
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.section import Section
from docx.shared import Inches, Length, Pt, RGBColor
from docx.styles.style import ParagraphStyle
from docx.text.paragraph import Paragraph
from docx.text.parfmt import ParagraphFormat

from ase.domain.report_documents import BlockKind, DocumentBlock, ReportDocument

INK = "17140F"
INK_SOFT = "635D53"
ACCENT = "97370F"
CAUTION_INK = "6B3F10"

STYLE_NAMES = {
    BlockKind.TITLE: "Title",
    BlockKind.HEADING: "Heading 1",
    BlockKind.ANNEX: "Heading 1",
    BlockKind.SUBHEADING: "Heading 2",
    BlockKind.TEXT: "Normal",
    BlockKind.METADATA: "ASE Metadata",
    BlockKind.WARNING: "ASE Review Warning",
    BlockKind.REFERENCE: "ASE Reference",
}


def _shade(paragraph: Paragraph, fill: str) -> None:
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), fill)
    paragraph.paragraph_format.element.get_or_add_pPr().append(shading)


def _border(target: Paragraph | ParagraphFormat, edge: str, colour: str, size: int) -> None:
    fmt = target.paragraph_format if isinstance(target, Paragraph) else target
    properties = fmt.element.get_or_add_pPr()
    borders = properties.find(qn("w:pBdr"))
    if borders is None:
        borders = OxmlElement("w:pBdr")
        properties.append(borders)
    element = OxmlElement(f"w:{edge}")
    element.set(qn("w:val"), "single")
    element.set(qn("w:sz"), str(size))
    element.set(qn("w:space"), "6")
    element.set(qn("w:color"), colour)
    borders.append(element)


def configure_styles(word: WordDocument) -> dict[BlockKind, str]:
    """A single typographic scale, so every document level stays distinguishable."""
    normal = word.styles["Normal"]
    if isinstance(normal, ParagraphStyle):
        normal.font.name, normal.font.size = "Aptos", Pt(10)
        normal.font.color.rgb = RGBColor.from_string(INK)
        normal.paragraph_format.space_after = Pt(7)
        normal.paragraph_format.line_spacing = 1.16
    for name, size, space_before, ink in (
        ("Title", 22, 0, INK),
        ("Heading 1", 14, 18, INK),
        ("Heading 2", 10.5, 12, ACCENT),
    ):
        style = word.styles[name]
        if isinstance(style, ParagraphStyle):
            style.font.name, style.font.size = "Aptos Display", Pt(size)
            style.font.color.rgb = RGBColor.from_string(ink)
            style.font.bold = True
            style.paragraph_format.keep_with_next = True
            style.paragraph_format.space_before = Pt(space_before)
            style.paragraph_format.space_after = Pt(3)
    heading = word.styles["Heading 1"]
    if isinstance(heading, ParagraphStyle):
        _border(heading.paragraph_format, "bottom", ACCENT, 8)
    metadata = word.styles.add_style("ASE Metadata", WD_STYLE_TYPE.PARAGRAPH)
    metadata.base_style = normal
    metadata.font.size, metadata.font.color.rgb = Pt(8.5), RGBColor.from_string(INK_SOFT)
    metadata.paragraph_format.space_after = Pt(2)
    eyebrow = word.styles.add_style("ASE Eyebrow", WD_STYLE_TYPE.PARAGRAPH)
    eyebrow.base_style = normal
    eyebrow.font.size, eyebrow.font.color.rgb = Pt(7.5), RGBColor.from_string(ACCENT)
    eyebrow.font.bold = True
    eyebrow.paragraph_format.space_after = Pt(1)
    warning = word.styles.add_style("ASE Review Warning", WD_STYLE_TYPE.PARAGRAPH)
    warning.base_style = normal
    warning.font.bold = True
    warning.font.size = Pt(9.5)
    warning.font.color.rgb = RGBColor.from_string(CAUTION_INK)
    warning.paragraph_format.space_before = Pt(8)
    reference = word.styles.add_style("ASE Reference", WD_STYLE_TYPE.PARAGRAPH)
    reference.base_style = normal
    reference.font.size = Pt(8.5)
    reference.paragraph_format.left_indent = Inches(0.26)
    reference.paragraph_format.first_line_indent = Inches(-0.26)
    reference.paragraph_format.space_after = Pt(5)
    return dict(STYLE_NAMES)


def add_masthead(
    word: WordDocument,
    head: list[DocumentBlock],
    render: Callable[[Paragraph, DocumentBlock], None],
) -> None:
    """Open the document the way the reader does: eyebrow, title, colophon, rule."""
    word.add_paragraph("INTELLIGENCE PRODUCT", style="ASE Eyebrow")
    for block in head:
        paragraph = word.add_paragraph(style=STYLE_NAMES[block.kind])
        render(paragraph, block)
    closing = word.add_paragraph(style="ASE Metadata")
    closing.paragraph_format.space_after = Pt(10)
    _border(closing, "bottom", INK, 12)


def add_section_number(paragraph: Paragraph, number: int) -> None:
    """The accent section number the reader shows beside each heading."""
    run = paragraph.add_run(f"{number:02d}   ")
    run.font.color.rgb = RGBColor.from_string(ACCENT)


def add_review_band(paragraph: Paragraph) -> None:
    """Give a review notice the same banded treatment the reader shows."""
    _shade(paragraph, "FDF4E2")
    for edge in ("top", "bottom", "left", "right"):
        _border(paragraph, edge, "CF9736", 6)


def add_page_furniture(word: WordDocument, document: ReportDocument) -> None:
    """A running head on every page and a numbered footer, as A4 documents expect."""
    section = word.sections[0]
    section.different_first_page_header_footer = True
    head = section.header.paragraphs[0]
    head.style = word.styles["ASE Metadata"]
    head.alignment = WD_ALIGN_PARAGRAPH.LEFT
    head.paragraph_format.tab_stops.add_tab_stop(_text_width(section), WD_TAB_ALIGNMENT.RIGHT)
    head.add_run(f"{document.title}\t{document.reference}")
    _border(head, "bottom", "D9D2C5", 4)
    for footer in (section.footer, section.first_page_footer):
        paragraph = footer.paragraphs[0]
        paragraph.style = word.styles["ASE Metadata"]
        paragraph.paragraph_format.tab_stops.add_tab_stop(
            _text_width(section), WD_TAB_ALIGNMENT.RIGHT
        )
        _border(paragraph, "top", "D9D2C5", 4)
        paragraph.add_run(f"{document.reference}\tPage ")
        _field(paragraph, "PAGE")
        paragraph.add_run(" of ")
        _field(paragraph, "NUMPAGES")


def _text_width(section: Section) -> Length:
    """The printable width, so a right tab stop lands on the right margin."""
    width = section.page_width or Inches(8.27)
    left = section.left_margin or Inches(0.78)
    right = section.right_margin or Inches(0.78)
    return Length(width - left - right)


def _field(paragraph: Paragraph, instruction: str) -> None:
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), instruction)
    paragraph._p.append(field)
