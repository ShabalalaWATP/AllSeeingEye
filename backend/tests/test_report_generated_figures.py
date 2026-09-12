"""Deterministic diagrams generated from a frozen report's citation graph."""

import io
import zipfile
from dataclasses import replace

from pypdf import PdfReader

from ase.adapters.reports.documents import ReportDocumentRenderer
from ase.adapters.reports.figure_validation import verify_figure
from ase.application.reports.document import build_document
from ase.application.reports.publication_figures import build_evidence_relationship_figure
from ase.application.reports.publication_markdown import render_document_markdown
from ase.domain.report_documents import BlockKind, ExportFormat
from report_documents_helpers import document_records


def useful_graph_records():
    record, version = document_records()
    body = replace(
        version.body,
        key_judgements=(
            version.body.key_judgements[0],
            replace(version.body.key_judgements[1], supporting_evidence=("E2", "E3")),
        ),
    )
    return record, replace(version, body=body)


def test_useful_citation_graph_produces_deterministic_valid_figure() -> None:
    record, version = useful_graph_records()
    first = build_document(record, version)
    second = build_document(record, version)
    block = next(block for block in first.blocks if block.kind is BlockKind.FIGURE)
    repeated = next(block for block in second.blocks if block.kind is BlockKind.FIGURE)
    assert block.figure is not None and repeated.figure is not None

    figure = block.figure
    verified = verify_figure(figure)
    assert verified.content == figure.content
    assert figure.content == repeated.figure.content
    assert figure.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert figure.citation_numbers == (1, 2, 3)
    assert "KJ 1 is supported by references 1, 2" in figure.alt_text
    assert "KJ 2 is supported by references 2, 3" in figure.alt_text
    assert len(figure.alt_text) < 1_000

    markdown = render_document_markdown(first)
    assert "### Evidence relationship map" in markdown
    assert "[1](#reference-1), [2](#reference-2), [3](#reference-3)" in markdown


def test_small_or_ambiguous_graph_does_not_produce_decorative_figure() -> None:
    record, version = document_records()
    one_judgement = replace(
        version,
        body=replace(version.body, key_judgements=version.body.key_judgements[:1]),
    )
    two_sources = replace(
        version,
        body=replace(
            version.body,
            key_judgements=(
                version.body.key_judgements[0],
                replace(version.body.key_judgements[1], supporting_evidence=("E2",)),
            ),
        ),
    )
    for candidate in (version, one_judgement, two_sources):
        document = build_document(record, candidate)
        assert all(block.kind is not BlockKind.FIGURE for block in document.blocks)


def test_contrary_relationship_is_described_and_untrusted_text_is_bounded() -> None:
    _, version = document_records()
    judgement = replace(
        version.body.key_judgements[1],
        statement="\x00" + "very long assessment " * 200,
        supporting_evidence=(),
        contradicting_evidence=("E3",),
    )
    body = replace(
        version.body,
        key_judgements=(version.body.key_judgements[0], judgement),
    )
    figure = build_evidence_relationship_figure(body, {"E1": 1, "E2": 2, "E3": 3})
    assert figure is not None
    assert "KJ 2 is contradicted by references 3" in figure.alt_text
    assert len(figure.alt_text) < 1_000
    assert verify_figure(figure).width == figure.width_px


def test_omitted_judgements_do_not_leave_disconnected_reference_nodes() -> None:
    _, version = document_records()
    first, second = version.body.key_judgements
    judgements = (
        first,
        replace(second, supporting_evidence=("E2", "E3")),
        replace(second, supporting_evidence=("E4",)),
        replace(second, supporting_evidence=("E5",)),
        replace(second, supporting_evidence=("E6",)),
        replace(second, supporting_evidence=("E1",)),
        replace(second, supporting_evidence=("E7",)),
    )
    body = replace(version.body, key_judgements=judgements)
    figure = build_evidence_relationship_figure(
        body, {f"E{number}": number for number in range(1, 8)}
    )
    assert figure is not None
    assert figure.citation_numbers == (1, 2, 3, 4, 5, 6)
    assert "reference 7" not in figure.alt_text


def test_generated_figure_exports_to_word_and_searchable_pdf() -> None:
    record, version = useful_graph_records()
    document = build_document(record, version)
    renderer = ReportDocumentRenderer()
    word = renderer.render(document, ExportFormat.DOCX)
    with zipfile.ZipFile(io.BytesIO(word)) as archive:
        assert any(name.startswith("word/media/") for name in archive.namelist())
    pdf = renderer.render(document, ExportFormat.PDF)
    text = "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages)
    assert "Evidence relationship map" in text
    assert "Figure 1. Relationships between" in text
