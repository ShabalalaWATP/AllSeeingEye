"""A diagram must render in every path, and read correctly where it cannot be drawn."""

from __future__ import annotations

import base64
import json
from dataclasses import replace

import pytest

from ase.adapters.reports.diagram_validation import verify_document_diagrams
from ase.adapters.reports.html_document import render_html
from ase.adapters.reports.markdown_package import render_markdown_export
from ase.adapters.reports.pdf import render_pdf
from ase.adapters.reports.word import render_docx
from ase.api.schemas_reports import ReportOut
from ase.application.reports.document import build_document
from ase.application.reports.render import render_markdown
from ase.domain.canonical_provenance import canonical_snapshot
from ase.domain.errors import InvalidRequest
from ase.domain.evidence import quality_of_information
from ase.domain.report_diagram_schema import parse_diagram
from ase.domain.report_documents import (
    BlockKind,
    DocumentBlock,
    DocumentDiagram,
    ReportDocument,
)
from ase.domain.report_records import ReportRecord, ReportVersion, body_to_dict
from ase.domain.reports import parse_body
from report_analysis_helpers import ACTOR_MAP, SERIES, TIMELINE
from report_documents_helpers import document_records

LABELS = frozenset({"E1", "E2", "E3"})


def _records() -> tuple[ReportRecord, ReportVersion]:
    record, version = document_records()
    labels = frozenset(item.label for item in version.evidence)
    diagram = parse_diagram(TIMELINE, labels)
    return record, replace(version, body=replace(version.body, diagrams=(diagram,)))


def test_the_document_places_the_drawing_and_its_equivalent_table_together() -> None:
    record, version = _records()
    document = build_document(record, version)
    kinds = [block.kind for block in document.blocks]
    index = kinds.index(BlockKind.DIAGRAM)
    assert kinds[index + 1] is BlockKind.TABLE
    block = document.blocks[index]
    assert block.diagram is not None
    assert block.text == block.diagram.alt_text
    table = document.blocks[index + 1].table
    assert table is not None and table.columns[-1] == "Source"
    assert len(table.rows) == len(version.body.diagrams[0].entries)


def test_the_report_response_carries_the_drawing_as_an_image_for_the_reader() -> None:
    """The web reader must receive the drawing, and receive it as encoded image bytes."""
    record, version = _records()
    payload = ReportOut.build(record, version).model_dump(mode="json")
    block = next(
        row for row in payload["version"]["publication"]["blocks"] if row["kind"] == "diagram"
    )
    diagram = block["diagram"]
    assert diagram is not None and diagram["media_type"] == "image/svg+xml"
    assert base64.b64decode(diagram["content_base64"]).decode("utf-8").startswith("<svg ")
    assert diagram["alt_text"] == block["text"] and diagram["title"]
    assert diagram["citation_numbers"]


def test_the_reader_html_inlines_the_vector_and_keeps_the_table() -> None:
    record, version = _records()
    html = render_html(build_document(record, version)).decode()
    assert "<figure><svg " in html
    assert "role='img'" in html and "aria-label=" in html
    assert "<table>" in html
    assert "<script" not in html


def test_the_portable_formats_carry_the_text_alternative_instead_of_the_drawing() -> None:
    record, version = _records()
    document = build_document(record, version)
    export = render_markdown_export(document, record.id, version.id, version.number)
    markdown = export.content.decode()
    assert version.body.diagrams[0].alt_text in markdown
    assert "| When | What was reported | Source |" in markdown
    assert render_pdf(document).startswith(b"%PDF")
    assert render_docx(document).startswith(b"PK")


def test_the_report_markdown_gains_a_diagram_section_with_its_table() -> None:
    record, version = _records()
    markdown = render_markdown(
        record.header,
        version.body,
        version.evidence,
        quality_of_information(version.evidence),
    )
    assert "## Diagrams" in markdown
    assert "| When | What was reported | Source |" in markdown
    assert "Timeline of three reported events" in markdown


def _stored(version: ReportVersion) -> dict[str, object]:
    """Exactly what persistence keeps: the body dictionary through JSON."""
    return json.loads(json.dumps(body_to_dict(version.body)))


def test_a_saved_diagram_survives_the_body_round_trip() -> None:
    _, version = _records()
    assert parse_body(_stored(version)).diagrams == version.body.diagrams


def test_a_stored_row_that_no_longer_validates_is_dropped_not_half_restored() -> None:
    _, version = _records()
    data = _stored(version)
    data["diagrams"][0]["entries"] = data["diagrams"][0]["entries"][:1]
    assert parse_body(data).diagrams == ()


def test_a_report_without_diagrams_keeps_its_provenance_bytes() -> None:
    _, version = _records()
    plain = replace(version, body=replace(version.body, diagrams=()))
    assert "diagrams" not in canonical_snapshot(plain)["body"]
    assert canonical_snapshot(version)["body"]["diagrams"]


@pytest.mark.parametrize("payload", [ACTOR_MAP, SERIES])
def test_every_shape_renders_into_the_reader_and_the_exports(payload: dict[str, object]) -> None:
    record, version = document_records()
    labels = frozenset(item.label for item in version.evidence)
    diagram = parse_diagram(payload, labels)
    version = replace(version, body=replace(version.body, diagrams=(diagram,)))
    document = build_document(record, version)
    assert b"%PDF" in render_pdf(document)[:8]
    html = render_html(document).decode()
    assert "<svg " in html and diagram.title in html


def test_generated_markup_outside_the_allowlist_is_refused_before_it_is_embedded() -> None:
    block = DocumentBlock(
        BlockKind.DIAGRAM,
        "A diagram",
        diagram=DocumentDiagram(
            title="Injected",
            caption="",
            alt_text="A diagram",
            svg="<svg xmlns='http://www.w3.org/2000/svg'><script>x()</script></svg>",
        ),
    )
    document = ReportDocument("Title", "Reference", (block,))
    with pytest.raises(InvalidRequest):
        verify_document_diagrams(document)
