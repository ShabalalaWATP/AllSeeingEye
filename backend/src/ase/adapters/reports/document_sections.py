"""Structural helpers shared by every report document renderer."""

from __future__ import annotations

from ase.domain.report_documents import BlockKind, DocumentBlock, ReportDocument


def leading_identity(document: ReportDocument) -> tuple[list[DocumentBlock], list[DocumentBlock]]:
    """Split the document into its opening title/metadata run and everything after.

    Every renderer presents that run as one identity block, so the reader, the PDF and
    the DOCX all open with the same masthead instead of three different first pages.
    """
    head: list[DocumentBlock] = []
    for block in document.blocks:
        if block.kind in {BlockKind.TITLE, BlockKind.METADATA}:
            head.append(block)
        else:
            break
    return head, list(document.blocks[len(head) :])
