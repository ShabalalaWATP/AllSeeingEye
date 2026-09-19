"""Reader-facing doctrine and assessments, projected only from the saved report version."""

from ase.application.reports.document_builder import DocumentBuilder
from ase.domain.doctrine import YARDSTICK, Probability
from ase.domain.evidence import EvidenceItem
from ase.domain.report_documents import BlockKind, DocumentTable, DocumentTableCell
from ase.domain.report_records import ReportVersion
from ase.domain.reports import KeyJudgement

RELIABILITY_LABELS = dict(
    zip(
        "ABCDEF",
        (
            "Completely reliable",
            "Usually reliable",
            "Fairly reliable",
            "Not usually reliable",
            "Unreliable",
            "Cannot be judged",
        ),
        strict=True,
    )
)
CREDIBILITY_LABELS = dict(
    enumerate(
        (
            "Confirmed by other sources",
            "Probably true",
            "Possibly true",
            "Doubtful",
            "Improbable",
            "Cannot be judged",
        ),
        start=1,
    )
)


def likelihood_label(probability: Probability) -> str:
    band = next(band for band in YARDSTICK if band.probability is probability)
    return f"{band.term} ({band.range_description})"


def likelihood_phrase(probability: Probability) -> str:
    """The plain yardstick words alone, capitalised to open a sentence: "Highly likely"."""
    term = next(band.term for band in YARDSTICK if band.probability is probability)
    return term[0].upper() + term[1:]


def key_to_terms(doc: DocumentBuilder) -> None:
    """The reading key, at the end, where the doctrine behind the plain words is named once."""
    doc.heading("Key to the terms")
    doc.add(
        "Likelihood words. Each judgement uses one of these words; the ranges are approximate "
        "bands, not measured probabilities:"
    )
    doc.list(
        [
            (f"{band.term[0].upper()}{band.term[1:]}: {band.range_description}.", ())
            for band in YARDSTICK
        ]
    )
    doc.add(
        "Confidence. High, moderate or low describes how strong and stable the basis for a "
        "judgement is, separately from how likely it is. A judgement can be likely and low "
        "confidence at once."
    )
    doc.add(
        "Source grades. A letter from A to F says how reliable the source has proved, and a "
        "number from 1 to 6 says how credible the particular item is. F and 6 mean there were "
        "not enough grounds to judge, not that the reporting was false."
    )
    doc.add(
        "These words follow the UK Professional Head of Intelligence Assessment (PHIA) "
        "probability yardstick and the Admiralty grading system described in UK and NATO "
        "doctrine. The application is informed by that public doctrine; it is not accredited "
        "and does not claim doctrinal compliance."
    )


def confidence_rationale(judgement: KeyJudgement, version: ReportVersion) -> str:
    """Remove a known generated preface only when its assessment is retained separately."""
    statement = judgement.confidence_statement
    marker = "Model rationale (unverified): "
    saved_judgement = version.assessment is not None and any(
        item.judgement_id == judgement.id for item in version.assessment.judgements
    )
    if (
        saved_judgement
        and statement.startswith("Engine confidence ceiling: ")
        and marker in statement
    ):
        return statement.partition(marker)[2]
    return statement


def source_assessment(doc: DocumentBuilder, version: ReportVersion) -> None:
    doc.heading("Source grades")
    numbers = doc.citation_numbers()
    evidence = sorted(
        (item for item in version.evidence if item.label in numbers),
        key=lambda item: numbers[item.label],
    )
    if not evidence:
        doc.add("No cited source items are available to display for this version.")
        return
    doc.add(
        "Each cited source carries a letter for how reliable it has proved and a number for "
        "how credible this item is. The key at the end explains both."
    )
    # Short tables keep native PDF rows readable; longer recorded explanations are prose.
    for offset in range(0, len(evidence), 8):
        rows = []
        for item in evidence[offset : offset + 8]:
            runs = doc.cited_runs(
                f"{item.source_name}: {item.title_en or item.title}", (item.label,)
            )
            rows.append(
                (
                    DocumentTableCell("".join(run.text for run in runs), runs),
                    DocumentTableCell(_reliability(item)),
                    DocumentTableCell(
                        f"{item.credibility}: "
                        f"{CREDIBILITY_LABELS.get(item.credibility, 'Not recorded')}"
                    ),
                )
            )
        doc.table(
            DocumentTable(
                "Recorded source grades" if offset == 0 else "Recorded source grades (continued)",
                ("Source item", "Source reliability", "Information credibility"),
                tuple(rows),
                "Grades are preserved from this report version; "
                "no source has been regraded on read.",
            )
        )
    doc.add("Recorded grading basis", BlockKind.SUBHEADING)
    for item in evidence:
        doc.cited(_basis(item), (item.label,))


def _reliability(item: EvidenceItem) -> str:
    label = f"{item.reliability}: {RELIABILITY_LABELS.get(item.reliability, 'Not recorded')}"
    rating = item.source_rating
    if rating is None:
        return f"Retained {item.reliability} grade. Source assessment basis not recorded."
    if rating.status == "unassessed":
        return f"Retained {item.reliability} feed grade; publisher reliability unassessed."
    return label + ". Recorded editorial assessment."


def _basis(item: EvidenceItem) -> str:
    rating = item.source_rating
    source = (
        f"Source assessment ({rating.status}): {rating.basis}"
        if rating is not None
        else "Source assessment basis was not recorded in this version."
    )
    if rating is not None and not rating.publisher_reliability_assessed:
        source += " This is not an assessment of the individual publisher or author."
    return (
        f"{item.source_name}. {source} "
        f"Item grading basis: {item.grade_rationale or 'Not recorded in this version.'}"
    )


def assessment_method(doc: DocumentBuilder, version: ReportVersion) -> None:
    doc.heading("How the assessment was made")
    doc.add(
        "Likelihood words and confidence levels are explained in the key at the end. "
        "Source reliability (A to F) and information credibility (1 to 6) follow the separate "
        "grading dimensions described in UK MOD JDP 2-00, fourth edition, Table 3.1."
    )
    assessment = version.assessment
    if assessment is None:
        doc.add(
            "A detailed evidence assessment was not recorded for this version. The saved "
            "judgements and item grades are shown as recorded; no confidence limit or "
            "corroboration assessment has been inferred retrospectively."
        )
        return
    doc.add(
        "The recorded evidence assessment is retained below. More articles do not automatically "
        "mean stronger support: copies and shared reporting origins are not independent "
        "confirmation, and weaker reporting does not outvote stronger evidence. "
        "The application constrains confidence from the information base; it cannot establish "
        "analytical rigour or fully measure complexity and volatility."
    )
    saved = {item.judgement_id: item for item in assessment.judgements}
    for index, judgement in enumerate(version.body.key_judgements, start=1):
        recorded = saved.get(judgement.id)
        doc.add(f"Judgement {index}: the evidence behind it", BlockKind.SUBHEADING)
        if recorded is None:
            doc.add("A detailed evidence assessment was not recorded for this judgement.")
            continue
        doc.add(
            f"Recorded evidence confidence limit: {recorded.confidence_ceiling.value}. "
            f"Recorded final analytical confidence: {recorded.final_confidence.value}."
        )
        labels = (*recorded.supporting_labels, *recorded.contradicting_labels)
        for explanation in recorded.explanation:
            doc.cited(explanation, labels)
        for limitation in recorded.limitations:
            if limitation not in assessment.limitations:
                doc.add(limitation)
        if recorded.improvements:
            doc.add("What would strengthen the assessment", BlockKind.SUBHEADING)
            doc.list([(text, ()) for text in recorded.improvements])
    if assessment.limitations:
        doc.add("Method limitations", BlockKind.SUBHEADING)
        doc.list([(text, ()) for text in assessment.limitations])
