"""Project one frozen report version into its professional reader product."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from ase.application.reports.export_text import review_notice
from ase.application.reports.frozen_header import frozen_period_line
from ase.application.reports.reference_projection import build_references, reference_text
from ase.domain.doctrine import term_for
from ase.domain.errors import InvalidRequest
from ase.domain.evidence import EvidenceItem
from ase.domain.report_documents import (
    BlockKind,
    DocumentBlock,
    DocumentInline,
    DocumentListItem,
    DocumentReference,
    DocumentTable,
    DocumentTableCell,
    ReportDocument,
)
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.reports import ReportBody, ReportStatus

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
        if numbers:
            marker = f"[{', '.join(str(number) for number in numbers)}]"
            runs.extend((DocumentInline(" "), DocumentInline(marker, "ltr", numbers)))
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
        projection = self._bounded(
            "\n".join(("\t".join(table.columns), *("\t".join(c.text for c in row) for row in rows)))
        )
        self.blocks.append(DocumentBlock(BlockKind.TABLE, projection, table=table))

    def references(self) -> tuple[DocumentReference, ...]:
        return build_references(self._numbers, self._evidence)


def _summary(doc: DocumentBuilder, body: ReportBody) -> None:
    doc.heading("Executive summary")
    if not body.key_judgements:
        doc.add("No assessed conclusion was produced for this report version.", BlockKind.WARNING)
        return
    rows = []
    for item in body.key_judgements:
        change_value = (
            item.change_from_previous.value.replace("_", " ")
            if item.change_from_previous is not None
            else None
        )
        change = (
            f" Change from previous assessment: {change_value}." if change_value is not None else ""
        )
        rows.append(
            (
                f"{item.statement} Assessment: {term_for(item.probability)}. "
                f"Confidence: {item.confidence.value}. {item.confidence_statement}{change}",
                item.supporting_evidence,
            )
        )
    doc.list(rows)
    contrary = [
        (
            f"Retained reporting challenges the judgement that {item.statement}",
            item.contradicting_evidence,
        )
        for item in body.key_judgements
        if item.contradicting_evidence
    ]
    if contrary:
        doc.add("Contrary reporting", BlockKind.SUBHEADING)
        doc.list(contrary)


def _findings(doc: DocumentBuilder, body: ReportBody) -> None:
    if not body.reporting and not body.assessment:
        return
    doc.heading("Findings and analysis")
    for theme in body.reporting:
        if theme.theme:
            doc.add(theme.theme, BlockKind.SUBHEADING)
        doc.list([(item.text, item.evidence) for item in theme.items])
    for section in body.assessment:
        if section.heading:
            doc.add(section.heading, BlockKind.SUBHEADING)
        if section.text:
            doc.cited(section.text, section.evidence)


def _alternatives(doc: DocumentBuilder, version: ReportVersion) -> None:
    alternatives = version.body.alternative_hypotheses
    if alternatives:
        doc.heading("Alternative explanations")
        doc.list(
            [
                (
                    f"{item.text} Why it is currently assessed as less likely: "
                    f"{item.why_less_likely}",
                    item.evidence,
                )
                for item in alternatives
            ]
        )
    advocacy = version.advocacy if version.challenge is None else None
    if advocacy is not None:
        if not alternatives:
            doc.heading("Alternative explanations")
        doc.cited(
            f"An alternative view is that {advocacy.argument} {advocacy.rationale}".strip(),
            advocacy.evidence,
        )


def _outlook(doc: DocumentBuilder, body: ReportBody) -> None:
    doc.heading("Outlook and indicators")
    condition = body.indicators_and_warning.watch_condition.value.replace("_", " ").capitalize()
    doc.add(f"Watch condition: {condition}.")
    indicators = tuple(
        dict.fromkeys(indicator for item in body.key_judgements for indicator in item.indicators)
    )
    if indicators:
        doc.add("Indicators to watch", BlockKind.SUBHEADING)
        doc.list([(indicator, ()) for indicator in indicators])
    if body.indicators_and_warning.changes:
        doc.add("Recent warning changes", BlockKind.SUBHEADING)
        doc.list([(change, ()) for change in body.indicators_and_warning.changes])
    if body.collection_recommendations:
        doc.add("Recommended next steps", BlockKind.SUBHEADING)
        doc.list([(item, ()) for item in body.collection_recommendations])


def _limitations(doc: DocumentBuilder, version: ReportVersion) -> None:
    doc.heading("Limitations and confidence")
    if version.status is not ReportStatus.READY:
        doc.add(review_notice(version.status), BlockKind.WARNING)
    else:
        doc.add(
            "Automated checks passed. Independent factual or analyst verification "
            "has not been recorded."
        )
    quality = version.quality
    doc.add(
        f"The report draws on {quality.items} retained source item(s) from "
        f"{quality.independent_organisations} declared organisation group(s). "
        "Organisational independence and factual accuracy have not been independently verified."
    )
    if quality.flagged:
        doc.add(
            f"{quality.flagged} source item(s) contain instruction-like text and require caution.",
            BlockKind.WARNING,
        )
    if version.body.assumptions:
        doc.add("Assumptions", BlockKind.SUBHEADING)
        doc.list(
            [
                (f"{item.text}{' This is a lynchpin assumption.' if item.lynchpin else ''}", ())
                for item in version.body.assumptions
            ]
        )
    if version.body.gaps:
        doc.add("Evidence gaps", BlockKind.SUBHEADING)
        doc.list([(item.text, ()) for item in version.body.gaps])
    if version.body.sourcing_statement:
        doc.add(version.body.sourcing_statement)


def build_document(record: ReportRecord, version: ReportVersion) -> ReportDocument:
    """Build the canonical product for the exact frozen version without new research."""
    if len(version.markdown) > MAX_DOCUMENT_CHARS * 2:
        raise InvalidRequest("This report exceeds the document export size limit.")
    doc = DocumentBuilder(version.evidence)
    reference = f"Report {record.id} | version {version.number}"
    doc.add(record.title, BlockKind.TITLE)
    doc.inline((DocumentInline(reference, "ltr"),), BlockKind.METADATA)
    doc.inline((DocumentInline(frozen_period_line(record, version), "ltr"),), BlockKind.METADATA)
    question = record.scope.get("question")
    if isinstance(question, str) and question.strip() and question.strip() not in record.title:
        doc.add("Research question", BlockKind.SUBHEADING)
        doc.add(question.strip())
    if version.status is ReportStatus.FAILED:
        doc.add(review_notice(version.status), BlockKind.WARNING)
    _summary(doc, version.body)
    _findings(doc, version.body)
    cited = version.body.cited_labels()
    doc.chronology([item for item in version.evidence if item.label in cited])
    _alternatives(doc, version)
    _outlook(doc, version.body)
    _limitations(doc, version)
    references = doc.references()
    if references:
        doc.heading("References")
        for item in references:
            doc.add(reference_text(item), BlockKind.REFERENCE)
    return ReportDocument(
        record.title,
        reference,
        tuple(doc.blocks),
        str(record.scope.get("report_language", "en")),
        references,
        1,
    )
