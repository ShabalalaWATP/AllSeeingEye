"""Embedded Chinese script fonts preserve text, dates, citations and pagination."""

import io
from dataclasses import replace

import pytest
from pypdf import PdfReader

from ase.adapters.reports.pdf import render_pdf
from ase.application.reports.document import build_document
from ase.domain.report_documents import BlockKind, DocumentBlock, ReportDocument
from report_documents_helpers import document_records


@pytest.mark.parametrize(
    ("language", "text"),
    [
        ("zh", "尚未确认交付。"),
        ("zh-Hans", "尚未确认交付。"),
        ("zh-Hant", "尚未確認交付。"),
    ],
)
def test_embedded_cjk_text_and_mixed_identifiers_round_trip(language: str, text: str) -> None:
    phrase = text + " 2026-09-06 [E1] 123"
    document = ReportDocument(
        "Research",
        "version 1",
        (
            DocumentBlock(BlockKind.TITLE, phrase),
            *(DocumentBlock(BlockKind.TEXT, phrase * 12) for _ in range(30)),
        ),
        language,
    )
    pdf = PdfReader(io.BytesIO(render_pdf(document)))
    extracted = "\n".join(page.extract_text() for page in pdf.pages)
    assert text in extracted
    assert "2026-09-06 [E1] 123" in extracted
    assert "[U+" not in extracted and "\x00" not in extracted
    assert len(pdf.pages) > 1
    assert all(not page.get("/Annots") for page in pdf.pages)


def test_document_selects_frozen_output_script_and_keeps_rtl_fallback() -> None:
    record, version = document_records()
    record.scope = {"report_language": "zh-Hant"}
    document = build_document(record, version)
    assert document.language == "zh-Hant"
    document = replace(document, blocks=(DocumentBlock(BlockKind.TEXT, "العربية"),))
    extracted = PdfReader(io.BytesIO(render_pdf(document))).pages[0].extract_text()
    assert "[U+0627]" in extracted
