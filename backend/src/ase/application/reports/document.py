"""Project one frozen report version into its reader product.

The document reads top to bottom the way a person wants it: what happened, what it means,
what we judge, other explanations, what to watch, what we are unsure about. The method,
the source grades and the doctrine behind the words sit at the end as notes and a key,
so the narrative is never interrupted by them.
"""

from __future__ import annotations

from ase.application.reports.document_assessment import (
    assessment_method,
    confidence_rationale,
    key_to_terms,
    likelihood_phrase,
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


def _picture(doc: DocumentBuilder, body: ReportBody) -> None:
    """What the sources reported, theme by theme, in plain words with its citations."""
    if not body.reporting:
        return
    doc.heading("What happened")
    for theme in body.reporting:
        if theme.theme:
            doc.add(theme.theme, BlockKind.SUBHEADING)
        doc.list([(item.text, item.evidence) for item in theme.items])


def _meaning(doc: DocumentBuilder, body: ReportBody) -> None:
    if not body.assessment:
        return
    doc.heading("What it means")
    for section in body.assessment:
        if section.heading:
            doc.add(section.heading, BlockKind.SUBHEADING)
        if section.text:
            doc.cited(section.text, section.evidence)


def _judgements(doc: DocumentBuilder, version: ReportVersion) -> None:
    body = version.body
    doc.heading("What we judge")
    if not body.key_judgements:
        doc.add("No assessed conclusion was produced for this report version.", BlockKind.WARNING)
        return
    for item in body.key_judgements:
        doc.cited(item.statement, item.supporting_evidence)
        change = ""
        if item.change_from_previous is not None:
            moved = item.change_from_previous.value.replace("_", " ")
            change = f" Compared with the previous assessment: {moved}."
        likelihood = likelihood_phrase(item.probability)
        doc.add(f"{likelihood}, with {item.confidence.value} confidence.{change}")
        if version.document_schema_version >= 2:
            # A citation concern stays beside the judgement it touches, not only in the notes.
            judgement_review(doc, version, item.id)
    contrary = [
        (
            f"Some reporting argues against the judgement that {item.statement}",
            item.contradicting_evidence,
        )
        for item in body.key_judgements
        if item.contradicting_evidence
    ]
    if contrary:
        doc.add("What argues against this", BlockKind.SUBHEADING)
        doc.list(contrary)


def _alternatives(doc: DocumentBuilder, version: ReportVersion) -> None:
    alternatives = version.body.alternative_hypotheses
    advocacy = version.advocacy if version.challenge is None else None
    if not alternatives and advocacy is None:
        return
    doc.heading("Other explanations")
    if alternatives:
        doc.list(
            [
                (f"{item.text} Why we think it less likely: {item.why_less_likely}", item.evidence)
                for item in alternatives
            ]
        )
    if advocacy is not None:
        doc.cited(
            f"Another reading is that {advocacy.argument} {advocacy.rationale}".strip(),
            advocacy.evidence,
        )


def _outlook(doc: DocumentBuilder, body: ReportBody) -> None:
    doc.heading("What to watch")
    condition = body.indicators_and_warning.watch_condition.value.replace("_", " ").capitalize()
    doc.add(f"Watch level: {condition}.")
    indicators = tuple(
        dict.fromkeys(indicator for item in body.key_judgements for indicator in item.indicators)
    )
    if indicators:
        doc.add("Signs that would change the picture", BlockKind.SUBHEADING)
        doc.list([(indicator, ()) for indicator in indicators])
    if body.indicators_and_warning.changes:
        doc.add("Recent changes", BlockKind.SUBHEADING)
        doc.list([(change, ()) for change in body.indicators_and_warning.changes])
    if body.collection_recommendations:
        doc.add("What would help next", BlockKind.SUBHEADING)
        doc.list([(item, ()) for item in body.collection_recommendations])


def _uncertainty(doc: DocumentBuilder, body: ReportBody) -> None:
    if not body.assumptions and not body.gaps:
        return
    doc.heading("What we are unsure about")
    if body.assumptions:
        doc.add("Assumptions we have made", BlockKind.SUBHEADING)
        doc.list(
            [
                (
                    item.text
                    + (" Much of the assessment rests on this one." if item.lynchpin else ""),
                    (),
                )
                for item in body.assumptions
            ]
        )
    if body.gaps:
        doc.add("What we could not find out", BlockKind.SUBHEADING)
        doc.list([(item.text, ()) for item in body.gaps])


def _notes(
    doc: DocumentBuilder,
    record: ReportRecord,
    version: ReportVersion,
    *,
    include_generated_figures: bool,
    reviewed_snapshot: SourceReviewSnapshot | None,
) -> None:
    """The method and the sources, after the narrative, for the reader who wants them."""
    doc.heading("Notes on method and sources")
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
    if version.body.sourcing_statement:
        doc.add(version.body.sourcing_statement)
    if version.canonical_requirements:
        doc.add("The research questions", BlockKind.SUBHEADING)
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
    for index, item in enumerate(version.body.key_judgements, start=1):
        rationale = confidence_rationale(item, version)
        doc.add(f"Judgement {index}: how confident we are and why", BlockKind.SUBHEADING)
        doc.add(
            f"{likelihood_phrase(item.probability)}, with {item.confidence.value} confidence. "
            + (
                f"Confidence rationale (not independently verified): {rationale}"
                if rationale
                else ""
            )
        )
    if include_generated_figures:
        figure = build_evidence_relationship_figure(version.body, doc.citation_numbers())
        if figure is not None:
            doc.figure(figure)
    cited = version.body.cited_labels()
    doc.chronology([item for item in version.evidence if item.label in cited])
    assessment_method(doc, version)
    source_assessment(doc, version)
    if reviewed_snapshot is not None:
        reviewed_source_assessment(doc, record, version, reviewed_snapshot)


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
        doc.add("The question", BlockKind.SUBHEADING)
        doc.add(question.strip())
    if version.document_schema_version >= 2:
        opening_review_notice(doc, version)
    elif version.status is ReportStatus.FAILED:
        doc.add(review_notice(version.status), BlockKind.WARNING)
    _picture(doc, version.body)
    _meaning(doc, version.body)
    for diagram in version.body.diagrams:
        doc.add("Diagram", BlockKind.SUBHEADING)
        doc.diagram(diagram)
    _judgements(doc, version)
    _alternatives(doc, version)
    _outlook(doc, version.body)
    _uncertainty(doc, version.body)
    _notes(
        doc,
        record,
        version,
        include_generated_figures=include_generated_figures,
        reviewed_snapshot=reviewed_snapshot,
    )
    key_to_terms(doc)
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
