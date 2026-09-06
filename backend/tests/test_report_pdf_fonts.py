"""Readable Latin, Greek and Cyrillic exports, with explicit unsupported-script fallback."""

import hashlib
import io
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from pypdf import PdfReader

from ase.adapters.reports.font_support import FONT_DIRECTORY, font_characters
from ase.adapters.reports.pdf import render_pdf
from ase.application.reports.document import build_document
from ase.domain.direction import Direction
from ase.domain.report_documents import BlockKind, DocumentBlock, ReportDocument
from report_documents_helpers import document_records

LATIN = "Crue à Lyon: 1 200 évacués, Straße fermée."
GREEK = "Η γέφυρα παραμένει κλειστή για έλεγχο."  # noqa: RUF001 - Greek fixture text
CYRILLIC = "Міст не зруйновано. Дорогу закрито до перевірки."
QUESTION = "Що відомо про стан мосту?"


def foreign_document() -> ReportDocument:
    record, version = document_records()
    record.title = "Перевірка джерел / Έλεγχος πηγών"
    evidence = (
        replace(version.evidence[0], title=CYRILLIC, summary=GREEK, language="uk"),
        replace(version.evidence[1], title=LATIN, language="fr"),
    )
    version = replace(version, evidence=evidence, direction=Direction(QUESTION, (), (), ()))
    return build_document(record, version)


def test_foreign_query_and_frozen_evidence_remain_readable_in_actual_export() -> None:
    pdf = PdfReader(io.BytesIO(render_pdf(foreign_document())))
    text = "\n".join(page.extract_text() for page in pdf.pages)
    for phrase in (LATIN, GREEK, CYRILLIC, QUESTION, "Перевірка джерел / Έλεγχος πηγών"):
        assert phrase in text
    assert "[U+" not in text


@pytest.mark.parametrize("text", ["مرحبا", "秘密", "かな", "한글", "\u202e"])
def test_unsupported_scripts_and_bidi_controls_remain_explicit(text: str) -> None:
    document = ReportDocument("Script coverage", "Fixture", (DocumentBlock(BlockKind.TEXT, text),))
    pdf = PdfReader(io.BytesIO(render_pdf(document)))
    output = "\n".join(page.extract_text() for page in pdf.pages)
    assert "".join(f"[U+{ord(character):04X}]" for character in text) in output
    assert "including Arabic and CJK" in output
    assert "DOCX export retains their original characters" in " ".join(output.split())


def test_both_weights_are_embedded_so_viewers_need_no_system_fonts() -> None:
    document = ReportDocument(
        "Fixture",
        "Fixture",
        (
            DocumentBlock(BlockKind.TITLE, "Перевірка"),
            DocumentBlock(BlockKind.TEXT, CYRILLIC),
        ),
    )
    pdf = PdfReader(io.BytesIO(render_pdf(document)))
    font_resources = pdf.pages[0]["/Resources"]["/Font"]
    embedded = []
    for reference in font_resources.values():
        font = reference.get_object()
        if "DejaVu" in font["/BaseFont"]:
            embedded.append(font["/BaseFont"])
            assert font["/FontDescriptor"]["/FontFile2"].get_data()
    assert len(embedded) == 2


def test_parallel_exports_keep_each_document_text_and_font_subsets() -> None:
    documents = [
        ReportDocument(
            "Fixture",
            "Fixture",
            (
                DocumentBlock(BlockKind.TITLE, f"Перевірка {number}"),
                DocumentBlock(BlockKind.TEXT, CYRILLIC + " " + GREEK),
            ),
        )
        for number in range(4)
    ]
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(render_pdf, documents))
    for number, result in enumerate(results):
        text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(result)).pages)
        assert f"Перевірка {number}" in text and CYRILLIC in text and GREEK in text


def test_font_assets_match_verified_upstream_and_include_required_notices() -> None:
    expected = {
        "DejaVuLGCSans.ttf": "321487efd1b5fa5bffc0597755708fb7b308b3a9a613cebaa013f6a9dd873ab8",
        "DejaVuLGCSans-Bold.ttf": (
            "0746f87aafab1227658d304e36dab999bfa95f2a6811a1031ca38ed243540a78"
        ),
        "LICENSE": "7a083b136e64d064794c3419751e5c7dd10d2f64c108fe5ba161eae5e5958a93",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((FONT_DIRECTORY / name).read_bytes()).hexdigest() == digest
    licence = (FONT_DIRECTORY / "LICENSE").read_text(encoding="utf-8")
    assert "Bitstream" in licence and "Tavmjong Bah" in licence
    characters = font_characters()
    assert all(ord(character) in characters for character in LATIN + GREEK + CYRILLIC)
