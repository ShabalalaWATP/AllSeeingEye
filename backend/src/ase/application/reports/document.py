"""Project a frozen report version into bounded, structured, plain-text document content."""

from __future__ import annotations

import json
from collections.abc import Sequence

from ase.application.reports.assessment_export import assessment_sections
from ase.application.reports.export_text import evidence_metadata, review_notice, safe_url
from ase.application.reports.frozen_header import frozen_period_line
from ase.domain.doctrine import term_for
from ase.domain.errors import InvalidRequest
from ase.domain.evidence import EvidenceItem
from ase.domain.report_documents import BlockKind, DocumentBlock, ReportDocument
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.reports import ReportBody, ReportStatus

MAX_DOCUMENT_CHARS = 300_000
MAX_BLOCK_CHARS = 16_000
MAX_BLOCKS = 2_000
MAX_EVIDENCE = 100


class DocumentBuilder:
    def __init__(self) -> None:
        self.blocks: list[DocumentBlock] = []
        self.characters = 0

    def add(self, text: str, kind: BlockKind = BlockKind.TEXT) -> None:
        self.characters += len(text)
        if (
            len(text) > MAX_BLOCK_CHARS
            or self.characters > MAX_DOCUMENT_CHARS
            or len(self.blocks) >= MAX_BLOCKS
        ):
            raise InvalidRequest("This report exceeds the document export size limit.")
        # XML 1.0 forbids control characters; preserve valid Unicode and line breaks.
        clean = "".join(
            c
            for c in text
            if c in "\n\t"
            or 32 <= ord(c) <= 0xD7FF
            or 0xE000 <= ord(c) <= 0xFFFD
            or 0x10000 <= ord(c) <= 0x10FFFF
        )
        self.blocks.append(DocumentBlock(kind, clean))

    def heading(self, text: str) -> None:
        self.add(text, BlockKind.HEADING)


def _cites(labels: Sequence[str]) -> str:
    return f" [{', '.join(labels)}]" if labels else ""


def _judgements(doc: DocumentBuilder, body: ReportBody) -> None:
    doc.heading("Key judgements")
    if not body.key_judgements:
        doc.add("No key judgements were produced.")
    for judgement in body.key_judgements:
        doc.add(judgement.id, BlockKind.SUBHEADING)
        doc.add(judgement.statement + _cites(judgement.supporting_evidence))
        doc.add(
            f"Probability: {term_for(judgement.probability)}. "
            f"Confidence: {judgement.confidence.value}. {judgement.confidence_statement}"
        )
        for label, values in (
            ("Contradicting evidence", judgement.contradicting_evidence),
            ("Assumptions", judgement.assumptions),
            ("Indicators", judgement.indicators),
        ):
            if values:
                doc.add(f"{label}: {'; '.join(values)}")
        if judgement.change_from_previous is not None:
            doc.add(f"Change from previous: {judgement.change_from_previous.value}.")


def _body(doc: DocumentBuilder, body: ReportBody) -> None:
    _judgements(doc, body)
    if body.reporting:
        doc.heading("Reporting")
        for theme in body.reporting:
            doc.add(theme.theme, BlockKind.SUBHEADING)
            for item in theme.items:
                grade = f" ({item.grade})" if item.grade else ""
                doc.add(item.text + _cites(item.evidence) + grade)
    if body.assessment:
        doc.heading("Assessment")
        for section in body.assessment:
            doc.add(section.heading, BlockKind.SUBHEADING)
            doc.add(section.text + _cites(section.evidence))
    if body.assumptions:
        doc.heading("Assumptions")
        for assumption in body.assumptions:
            flag = " (lynchpin)" if assumption.lynchpin else ""
            doc.add(f"{assumption.id}: {assumption.text}{flag}")
    if body.alternative_hypotheses:
        doc.heading("Alternative hypotheses")
        for alternative in body.alternative_hypotheses:
            doc.add(alternative.text + _cites(alternative.evidence))
            doc.add(f"Why less likely: {alternative.why_less_likely}")
    _closing(doc, body)


def _closing(doc: DocumentBuilder, body: ReportBody) -> None:
    doc.heading("Indicators and warning")
    doc.add(f"Watch condition: {body.indicators_and_warning.watch_condition.value}.")
    for change in body.indicators_and_warning.changes:
        doc.add(change)
    if body.gaps or body.collection_recommendations:
        doc.heading("Gaps and collection")
        for gap in body.gaps:
            doc.add(f"{gap.eei}: {gap.text}" if gap.eei else gap.text)
        for recommendation in body.collection_recommendations:
            doc.add(f"Recommend: {recommendation}")
    doc.heading("Sourcing statement")
    doc.add(body.sourcing_statement or "Not provided.")


def _evidence(doc: DocumentBuilder, items: Sequence[EvidenceItem]) -> None:
    if len(items) > MAX_EVIDENCE:
        raise InvalidRequest("This report exceeds the evidence export limit.")
    doc.add("Frozen evidence annex", BlockKind.ANNEX)
    if not items:
        doc.add("No frozen evidence.")
    for item in items:
        doc.add(f"{item.label} | {item.grade} | {item.source_name}", BlockKind.SUBHEADING)
        doc.add(f"Original title: {item.title}")
        if item.title_en:
            doc.add(f"Translation (unverified): {item.title_en}")
        if item.summary:
            doc.add(f"Source snippet: {item.summary}")
        doc.add("\n".join(evidence_metadata(item)), BlockKind.METADATA)
        for name, value in (("Source URL", item.url), ("Archive URL", item.archive_url)):
            if value:
                doc.add(
                    f"{name}: {safe_url(value) or 'Unavailable (unsafe URL)'}", BlockKind.METADATA
                )
        if item.flags:
            doc.add(f"Flags: {'; '.join(item.flags)}", BlockKind.WARNING)


def build_document(record: ReportRecord, version: ReportVersion) -> ReportDocument:
    if len(version.markdown) > MAX_DOCUMENT_CHARS * 2:
        raise InvalidRequest("This report exceeds the document export size limit.")
    doc = DocumentBuilder()
    reference = f"Report {record.id} | version {version.number}"
    doc.add(record.title, BlockKind.TITLE)
    doc.add(reference, BlockKind.METADATA)
    doc.add(frozen_period_line(record, version), BlockKind.METADATA)
    if record.scope:
        doc.add(f"Scope: {json.dumps(dict(record.scope), sort_keys=True)}", BlockKind.METADATA)
    doc.add(
        f"Status: {version.status.value.replace('_', ' ')}. "
        f"Created: {version.created_at.isoformat()}. "
        f"Model: {version.model}. Attempts: {version.attempts}.",
        BlockKind.METADATA,
    )
    doc.add(
        review_notice(version.status),
        BlockKind.METADATA if version.status is ReportStatus.READY else BlockKind.WARNING,
    )
    doc.add(
        "Frozen feed metadata and snippets. Source content and translations "
        "have not been independently verified."
    )
    if version.direction is not None:
        doc.heading("Direction")
        for line in version.direction.lines():
            doc.add(line)
        if version.direction.search_terms:
            doc.add(f"Search terms: {', '.join(version.direction.search_terms)}")
        if version.direction.categories:
            doc.add(f"Collection categories: {', '.join(version.direction.categories)}")
    _body(doc, version.body)
    if version.advocacy is not None:
        advocacy = version.advocacy
        doc.heading("Devil's advocacy")
        doc.add(
            f"Contrarian view on {advocacy.target}: {advocacy.argument}" + _cites(advocacy.evidence)
        )
        doc.add(advocacy.rationale or "No rationale provided.")
        doc.add(
            f"Confidence before: {advocacy.confidence_before or 'unchanged'}; "
            f"after: {advocacy.confidence_after or 'unchanged'}."
        )
    for heading, paragraphs in assessment_sections(version.assessment):
        doc.heading(heading)
        for paragraph in paragraphs:
            doc.add(paragraph)
    doc.heading("Quality of information")
    doc.add(version.quality.describe())
    if version.findings:
        doc.heading("Validator findings")
        for finding in version.findings:
            doc.add(
                f"{finding.severity.value}: {finding.rule}, {finding.location}: {finding.message}"
            )
    _evidence(doc, version.evidence)
    return ReportDocument(record.title, reference, tuple(doc.blocks))
