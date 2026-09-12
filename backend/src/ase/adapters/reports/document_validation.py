"""Renderer-side size limits for every string in the semantic document."""

from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import ReportDocument

MAX_DOCUMENT_CHARACTERS = 300_000
MAX_DOCUMENT_BLOCKS = 2_000
MAX_ELEMENT_CHARACTERS = 16_000


def validate_document_content(document: ReportDocument) -> None:
    values = [document.title, document.reference]
    for block in document.blocks:
        values.append(block.text)
        values.extend(item.text for item in block.items)
        if block.table:
            values.extend((block.table.title, block.table.caption, *block.table.columns))
            values.extend(cell.text for row in block.table.rows for cell in row)
        if block.figure:
            values.extend((block.figure.title, block.figure.caption, block.figure.alt_text))
    for reference in document.references:
        values.extend(
            (
                reference.evidence_label,
                reference.title,
                reference.publisher,
                reference.published_at or "",
                reference.accessed_at,
                reference.url or "",
                reference.archive_url or "",
                reference.original_title or "",
                reference.language or "",
            )
        )
    if (
        len(document.blocks) > MAX_DOCUMENT_BLOCKS
        or any(len(value) > MAX_ELEMENT_CHARACTERS for value in values)
        or sum(len(value) for value in values) > MAX_DOCUMENT_CHARACTERS
    ):
        raise InvalidRequest("This report exceeds the document rendering size limit.")
