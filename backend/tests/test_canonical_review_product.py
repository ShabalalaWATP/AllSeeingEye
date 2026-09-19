"""Material frozen review concerns survive the common reader and export projection."""

import io
from dataclasses import replace

from docx import Document
from pypdf import PdfReader

from ase.adapters.reports.documents import ReportDocumentRenderer
from ase.application.reports.document import build_document
from ase.application.reports.publication_markdown import render_document_markdown
from ase.domain.citation_checks import (
    CitationCheck,
    CitationStatus,
    JudgementCitationCheck,
    ReportCitationChecks,
)
from ase.domain.report_documents import ExportFormat
from ase.domain.reports import ReportStatus
from test_challenge_integration import challenge_records


def test_challenge_and_citation_concern_are_prominent_in_every_report_format() -> None:
    record, version = challenge_records()
    citation = JudgementCitationCheck(
        "KJ1",
        CitationStatus.REVIEW_REQUIRED,
        (
            CitationCheck(
                "E1",
                "supporting",
                CitationStatus.REVIEW_REQUIRED,
                version.evidence[0].event_id,
                version.evidence[0].content_hash,
                None,
                (),
                ("The source wording needs an attribution check.",),
            ),
        ),
        (),
    )
    version = replace(
        version,
        citation_checks=ReportCitationChecks("frozen-check-v1", (citation,)),
        status=ReportStatus.NEEDS_REVIEW,
        document_schema_version=2,
    )
    product = build_document(record, version)
    texts = [block.text for block in product.blocks]
    assert next(i for i, text in enumerate(texts) if "NEEDS REVIEW" in text) < texts.index(
        "What we judge"
    )
    assert "A key judgement has a literal source mismatch to review." in texts
    claim_index = next(
        i for i, text in enumerate(texts) if version.body.key_judgements[0].statement in text
    )
    concern_index = next(i for i, text in enumerate(texts) if "Citation review" in text)
    alternative_index = next(i for i, text in enumerate(texts) if "A different explanation" in text)
    assert claim_index < concern_index < alternative_index < texts.index("What to watch")
    renderer = ReportDocumentRenderer()
    markdown = render_document_markdown(product)
    word = Document(io.BytesIO(renderer.render(product, ExportFormat.DOCX)))
    pdf = PdfReader(io.BytesIO(renderer.render(product, ExportFormat.PDF)))
    word_text = "\n".join(paragraph.text for paragraph in word.paragraphs)
    pdf_text = "\n".join(page.extract_text() for page in pdf.pages)
    for rendered in (markdown, word_text, pdf_text):
        assert "Citation review" in rendered
        assert "A different explanation" in rendered
        assert "NEEDS REVIEW" in rendered
        assert "A key judgement has a literal source mismatch to review." in rendered
        assert "frozen-check-v1" not in rendered
        assert "saved-challenge-v0" not in rendered


def test_legacy_frozen_document_keeps_its_original_projection() -> None:
    record, version = challenge_records()
    assert version.document_schema_version == 1
    product = build_document(record, version)
    texts = [block.text for block in product.blocks]
    assert "What we judge" in texts
    assert all("Alternative view to test" not in text for text in texts)
    assert all("Citation review" not in text for text in texts)
    assert all("NEEDS REVIEW" not in text for text in texts[: texts.index("What we judge")])
