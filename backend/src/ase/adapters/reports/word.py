"""A4 Word document with semantic headings, paragraph flow and a version footer."""

from __future__ import annotations

import io

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor
from docx.styles.style import ParagraphStyle

from ase.domain.report_documents import BlockKind, ReportDocument


def render_docx(document: ReportDocument) -> bytes:
    word = Document()
    section = word.sections[0]
    section.page_width, section.page_height = Inches(8.27), Inches(11.69)
    section.top_margin = section.bottom_margin = Inches(0.65)
    section.left_margin = section.right_margin = Inches(0.7)
    normal = word.styles["Normal"]
    if isinstance(normal, ParagraphStyle):
        normal.font.name, normal.font.size = "Calibri", Pt(10)
        normal.paragraph_format.space_after = Pt(7)
        normal.paragraph_format.line_spacing = 1.12
    for name, size in (("Title", 22), ("Heading 1", 14), ("Heading 2", 11)):
        style = word.styles[name]
        if isinstance(style, ParagraphStyle):
            style.font.name, style.font.size = "Calibri", Pt(size)
            style.font.color.rgb = RGBColor.from_string("000000")
            style.paragraph_format.keep_with_next = True
    metadata = word.styles.add_style("ASE Metadata", WD_STYLE_TYPE.PARAGRAPH)
    metadata.base_style = normal
    metadata.font.size, metadata.font.color.rgb = Pt(8.5), RGBColor.from_string("424B57")
    warning = word.styles.add_style("ASE Review Warning", WD_STYLE_TYPE.PARAGRAPH)
    warning.base_style = normal
    warning.font.bold = True
    warning.font.color.rgb = RGBColor.from_string("853200")
    style_names = {
        BlockKind.TITLE: "Title",
        BlockKind.HEADING: "Heading 1",
        BlockKind.ANNEX: "Heading 1",
        BlockKind.SUBHEADING: "Heading 2",
        BlockKind.TEXT: "Normal",
        BlockKind.METADATA: "ASE Metadata",
        BlockKind.WARNING: "ASE Review Warning",
    }
    for block in document.blocks:
        paragraph = word.add_paragraph(block.text, style_names[block.kind])
        paragraph.paragraph_format.widow_control = True
        if block.kind is BlockKind.ANNEX:
            paragraph.paragraph_format.page_break_before = True
    footer = section.footer.paragraphs[0]
    footer.style = word.styles["ASE Metadata"]
    footer.add_run(f"{document.reference} | page ")
    field = OxmlElement("w:fldSimple")
    field.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}instr", "PAGE")
    footer._p.append(field)
    word.core_properties.title = document.title
    word.core_properties.author = "The All Seeing Eye"
    word.core_properties.subject = document.reference
    word.core_properties.comments = ""
    stream = io.BytesIO()
    word.save(stream)
    return stream.getvalue()
