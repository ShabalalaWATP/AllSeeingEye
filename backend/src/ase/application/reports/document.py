"""Project one frozen report version into its professional reader product."""

from __future__ import annotations

from ase.application.reports.document_assessment import (
    assessment_method,
    confidence_rationale,
    likelihood_label,
    source_assessment,
)
from ase.application.reports.document_builder import (
    MAX_BLOCK_CHARS,
    MAX_BLOCKS,
    MAX_DOCUMENT_CHARS,
    MAX_EVIDENCE,
    DocumentBuilder,
)
from ase.application.reports.document_review import judgement_review, opening_review_notice
from ase.application.reports.export_text import review_notice
from ase.application.reports.frozen_header import frozen_period_line
from ase.application.reports.publication_figures import build_evidence_relationship_figure
from ase.application.reports.reference_projection import reference_text
from ase.application.reports.reviewed_source_document import reviewed_source_assessment
from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import BlockKind, DocumentInline, ReportDocument
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.reports import ReportBody, ReportStatus
from ase.domain.source_review_records import SourceReviewSnapshot

__all__ = [
    "MAX_BLOCKS",
    "MAX_BLOCK_CHARS",
    "MAX_DOCUMENT_CHARS",
    "MAX_EVIDENCE",
    "DocumentBuilder",
    "build_document",
]


def _summary(doc: DocumentBuilder, version: ReportVersion) -> None:
    body = version.body
    doc.heading("Executive summary")
    if not body.key_judgements:
        doc.add("No assessed conclusion was produced for this report version.", BlockKind.WARNING)
        return
    for item in body.key_judgements:
        change_value = (
            item.change_from_previous.value.replace("_", " ")
            if item.change_from_previous is not None
            else None
        )
        change = (
            f" Change from previous assessment: {change_value}." if change_value is not None else ""
        )
        doc.cited(item.statement, item.supporting_evidence)
        doc.add(f"Likelihood (PHIA): {likelihood_label(item.probability)}.")
        doc.add(f"Analytical confidence: {item.confidence.value}.")
        rationale = confidence_rationale(item, version)
        if rationale:
            doc.add(f"Confidence rationale (not independently verified): {rationale}{change}")
        elif change:
            doc.add(change.strip())
        if version.document_schema_version >= 2:
            judgement_review(doc, version, item.id)
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
        doc.list(
            [
                (
                    f"{item.text} Recorded source grade(s): {item.grade or 'not recorded'}.",
                    item.evidence,
                )
                for item in theme.items
            ]
        )
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


def build_document(
    record: ReportRecord,
    version: ReportVersion,
    *,
    include_generated_figures: bool = True,
    reviewed_snapshot: SourceReviewSnapshot | None = None,
) -> ReportDocument:
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
    if version.canonical_requirements:
        doc.add("Research requirements", BlockKind.SUBHEADING)
        doc.list(
            [
                (
                    f"{row.id} ({'required' if row.required else 'optional'}, "
                    f"priority {row.priority}): {row.question}",
                    (),
                )
                for row in version.canonical_requirements
            ]
        )
    if version.document_schema_version >= 2:
        opening_review_notice(doc, version)
    elif version.status is ReportStatus.FAILED:
        doc.add(review_notice(version.status), BlockKind.WARNING)
    _summary(doc, version)
    if include_generated_figures:
        figure = build_evidence_relationship_figure(version.body, doc.citation_numbers())
        if figure is not None:
            doc.figure(figure)
    _findings(doc, version.body)
    for diagram in version.body.diagrams:
        doc.add("Diagram", BlockKind.SUBHEADING)
        doc.diagram(diagram)
    cited = version.body.cited_labels()
    doc.chronology([item for item in version.evidence if item.label in cited])
    _alternatives(doc, version)
    _outlook(doc, version.body)
    _limitations(doc, version)
    assessment_method(doc, version)
    source_assessment(doc, version)
    if reviewed_snapshot is not None:
        reviewed_source_assessment(doc, record, version, reviewed_snapshot)
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
