"""Bounded canonical report blocks and first-citation reference numbering."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from ase.application.reports.diagram_svg import render_diagram_svg
from ase.application.reports.diagram_text import project_diagram
from ase.application.reports.reference_projection import build_references
from ase.domain.errors import InvalidRequest
from ase.domain.evidence import EvidenceItem
from ase.domain.report_diagrams import ReportDiagram
from ase.domain.report_documents import (
    BlockKind,
    DocumentBlock,
    DocumentDiagram,
    DocumentFigure,
    DocumentInline,
    DocumentListItem,
    DocumentReference,
    DocumentTable,
    DocumentTableCell,
)

MAX_DOCUMENT_CHARS = 300_000
MAX_BLOCK_CHARS = 16_000
MAX_BLOCKS = 2_000
MAX_EVIDENCE = 100


def _clean(text: str) -> str:
    """Keep the shared projection XML-compatible without interpreting markup."""
    return "".join(
        char
        for char in text
        if char in "\n\t"
        or 32 <= ord(char) <= 0xD7FF
        or 0xE000 <= ord(char) <= 0xFFFD
        or 0x10000 <= ord(char) <= 0x10FFFF
    )


def _date(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).date().isoformat() if value.tzinfo else value.date().isoformat()


class DocumentBuilder:
    """Build bounded blocks and a deterministic first-citation reference registry."""

    def __init__(self, evidence: Sequence[EvidenceItem] = ()) -> None:
        if len(evidence) > MAX_EVIDENCE:
            raise InvalidRequest("This report exceeds the evidence export limit.")
        self.blocks: list[DocumentBlock] = []
        self.characters = 0
        self._evidence = {item.label: item for item in evidence}
        self._numbers: dict[str, int] = {}

    def _bounded(self, text: str) -> str:
        cleaned = _clean(text)
        self.characters += len(cleaned)
        if (
            len(cleaned) > MAX_BLOCK_CHARS
            or self.characters > MAX_DOCUMENT_CHARS
            or len(self.blocks) >= MAX_BLOCKS
        ):
            raise InvalidRequest("This report exceeds the document export size limit.")
        return cleaned

    def add(self, text: str, kind: BlockKind = BlockKind.TEXT) -> None:
        self.blocks.append(DocumentBlock(kind, self._bounded(text)))

    def inline(self, runs: tuple[DocumentInline, ...], kind: BlockKind = BlockKind.TEXT) -> None:
        cleaned = tuple(
            DocumentInline(_clean(run.text), run.direction, run.citation_numbers) for run in runs
        )
        text = self._bounded("".join(run.text for run in cleaned))
        self.blocks.append(DocumentBlock(kind, text, cleaned))

    def heading(self, text: str) -> None:
        self.add(text, BlockKind.HEADING)

    def diagram(self, diagram: ReportDiagram) -> None:
        """Draw the validated data, then always place its equivalent table beside it."""
        projection = project_diagram(diagram)
        numbers = self._citations(diagram.evidence_labels())
        self.blocks.append(
            DocumentBlock(
                BlockKind.DIAGRAM,
                self._bounded(diagram.alt_text),
                diagram=DocumentDiagram(
                    title=diagram.title,
                    caption=projection.caption,
                    alt_text=diagram.alt_text,
                    svg=render_diagram_svg(diagram),
                    citation_numbers=numbers,
                ),
            )
        )
        rows = tuple(
            (
                *(DocumentTableCell(_clean(value)) for value in cells),
                self._source_cell(evidence),
            )
            for cells, evidence in projection.rows
        )
        self.table(DocumentTable(projection.title, projection.columns, rows, projection.caption))

    def _source_cell(self, evidence: Sequence[str]) -> DocumentTableCell:
        runs = self.cited_runs(", ".join(evidence), evidence)
        return DocumentTableCell("".join(run.text for run in runs), runs)

    def figure(self, figure: DocumentFigure) -> None:
        self.blocks.append(
            DocumentBlock(BlockKind.FIGURE, self._bounded(figure.caption), figure=figure)
        )

    def citation_numbers(self) -> dict[str, int]:
        return dict(self._numbers)

    def _citations(self, labels: Sequence[str]) -> tuple[int, ...]:
        numbers: list[int] = []
        for label in labels:
            if label not in self._evidence:
                continue
            if label not in self._numbers:
                self._numbers[label] = len(self._numbers) + 1
            number = self._numbers[label]
            if number not in numbers:
                numbers.append(number)
        return tuple(numbers)

    def cited_runs(self, text: str, labels: Sequence[str]) -> tuple[DocumentInline, ...]:
        numbers = self._citations(labels)
        runs = [DocumentInline(_clean(text))]
        for offset in range(0, len(numbers), 32):
            batch = numbers[offset : offset + 32]
            marker = f"[{', '.join(str(number) for number in batch)}]"
            runs.extend((DocumentInline(" "), DocumentInline(marker, "ltr", batch)))
        return tuple(runs)

    def cited(self, text: str, labels: Sequence[str]) -> None:
        self.inline(self.cited_runs(text, labels))

    def list(self, rows: Sequence[tuple[str, Sequence[str]]], *, ordered: bool = False) -> None:
        items: list[DocumentListItem] = []
        for text, labels in rows:
            if not text.strip():
                continue
            runs = self.cited_runs(text, labels)
            items.append(DocumentListItem("".join(run.text for run in runs), runs))
        if not items:
            return
        projection = self._bounded("\n".join(item.text for item in items))
        self.blocks.append(
            DocumentBlock(BlockKind.LIST, projection, items=tuple(items), ordered=ordered)
        )

    def chronology(self, items: Sequence[EvidenceItem]) -> None:
        rows: list[tuple[DocumentTableCell, ...]] = []
        for item in sorted(
            items, key=lambda row: row.observed_at or row.published_at or row.captured_at
        ):
            occurred = item.observed_at or item.published_at
            runs = self.cited_runs(item.title_en or item.title, (item.label,))
            rows.append(
                (
                    DocumentTableCell(_date(occurred) or "Date not reported"),
                    DocumentTableCell(item.source_name),
                    DocumentTableCell("".join(run.text for run in runs), runs),
                )
            )
        if len(rows) < 2:
            return
        table = DocumentTable(
            "Source chronology",
            ("Date", "Source", "Reported item"),
            tuple(rows),
            "Chronology of dated material cited in this report. Dates are source-reported.",
        )
        self.table(table)

    def references(self) -> tuple[DocumentReference, ...]:
        return build_references(self._numbers, self._evidence)

    def table(self, table: DocumentTable) -> None:
        """Clean and bound structured cells as well as their plain-text projection."""
        rows = tuple(
            tuple(
                DocumentTableCell(
                    _clean(cell.text),
                    tuple(
                        DocumentInline(_clean(run.text), run.direction, run.citation_numbers)
                        for run in cell.inlines
                    ),
                )
                for cell in row
            )
            for row in table.rows
        )
        cleaned = DocumentTable(
            _clean(table.title),
            tuple(_clean(value) for value in table.columns),
            rows,
            _clean(table.caption),
        )
        projection = self._bounded(
            "\n".join(
                (
                    cleaned.title,
                    cleaned.caption,
                    "\t".join(cleaned.columns),
                    *("\t".join(cell.text for cell in row) for row in rows),
                )
            )
        )
        self.blocks.append(DocumentBlock(BlockKind.TABLE, projection, table=cleaned))
