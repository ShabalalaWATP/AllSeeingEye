"""Present one explicitly selected, frozen reviewer snapshot beside saved report grades."""

from ase.application.reports.document_assessment import CREDIBILITY_LABELS, RELIABILITY_LABELS
from ase.application.reports.document_builder import DocumentBuilder
from ase.domain.errors import InvalidRequest
from ase.domain.report_documents import BlockKind, DocumentTable, DocumentTableCell
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.source_assessment_bindings import assert_source_assessment_matches
from ase.domain.source_review_records import SourceReviewSnapshot


def validate_reviewed_snapshot(
    record: ReportRecord, version: ReportVersion, snapshot: SourceReviewSnapshot
) -> None:
    """Reject cross-report, cross-version or changed-capture projections before display."""
    if (
        not isinstance(snapshot, SourceReviewSnapshot)
        or snapshot.report_id != record.id
        or snapshot.report_version_id != version.id
        or snapshot.scope.team_id != record.team_id
        or (record.team_id is None and snapshot.scope.owner_id != record.created_by)
    ):
        raise InvalidRequest("The selected source snapshot does not match this report version.")
    try:
        assert_source_assessment_matches(
            snapshot.projection,
            report_version_id=version.id,
            body=version.body,
            evidence=version.evidence,
        )
    except (TypeError, ValueError) as exc:
        raise InvalidRequest(
            "The selected source snapshot does not match frozen evidence."
        ) from exc


def reviewed_source_assessment(
    doc: DocumentBuilder,
    record: ReportRecord,
    version: ReportVersion,
    snapshot: SourceReviewSnapshot,
) -> None:
    validate_reviewed_snapshot(record, version, snapshot)
    doc.heading("Reviewed source assessment snapshot")
    doc.add(
        f"Selected snapshot {snapshot.id}, frozen {snapshot.created_at.date().isoformat()}. "
        "These reviews concern the cited source and assertion within each saved judgement. "
        "They do not change the original report grades, analytical confidence, likelihood "
        "or publication decision. Missing reviews remain unassessed."
    )
    evidence_by_capture = {row.capture_id: row for row in snapshot.projection.evidence}
    saved_evidence = {row.label: row for row in version.evidence}
    assessments = {(row.evidence_id, row.claim_id): row for row in snapshot.projection.assessments}
    for claim in snapshot.projection.claims:
        doc.add(f"Judgement {claim.judgement_id}, subject: {claim.subject}", BlockKind.SUBHEADING)
        rows: list[tuple[DocumentTableCell, ...]] = []
        for use in claim.uses:
            captured = evidence_by_capture[use.capture_id]
            item = saved_evidence[captured.label]
            assessment = assessments[(use.capture_id, claim.claim_id)]
            runs = doc.cited_runs(
                f"{item.source_name}: {item.title_en or item.title}", (item.label,)
            )
            reliability = assessment.reliability.value
            credibility = assessment.credibility.value
            authenticity = (
                assessment.authenticity.status.value
                if assessment.authenticity is not None
                else "not reviewed"
            )
            rows.append(
                (
                    DocumentTableCell("".join(run.text for run in runs), runs),
                    DocumentTableCell(", ".join(use.roles)),
                    DocumentTableCell(
                        f"{reliability}: {RELIABILITY_LABELS[reliability]}"
                        if assessment.source_revision is not None
                        else "F: Cannot be judged, no scoped review"
                    ),
                    DocumentTableCell(
                        f"{credibility}: {CREDIBILITY_LABELS[credibility]}"
                        if assessment.assertion_revision is not None
                        else "6: Cannot be judged, no assertion review"
                    ),
                    DocumentTableCell(authenticity),
                )
            )
            for title, revision in (
                ("Source reliability", assessment.source_revision),
                ("Assertion credibility", assessment.assertion_revision),
            ):
                if revision is not None:
                    reviewed_on = revision.review.reviewed_at or revision.review.recorded_at
                    doc.cited(
                        f"{title} review for {item.source_name}: {revision.review.basis} "
                        f"Reviewed {reviewed_on.date().isoformat()}; "
                        f"policy {revision.review.policy_version}.",
                        (item.label,),
                    )
            if assessment.authenticity is not None:
                doc.cited(
                    f"Issuer authenticity review for {item.source_name}: "
                    f"{assessment.authenticity.basis}",
                    (item.label,),
                )
        for offset in range(0, len(rows), 8):
            doc.table(
                DocumentTable(
                    "Scoped reviewer assessments",
                    (
                        "Cited item",
                        "Role",
                        "Source reliability",
                        "Assertion credibility",
                        "Issuer authenticity",
                    ),
                    tuple(rows[offset : offset + 8]),
                    "Qualitative reviews frozen in the selected exact-version snapshot.",
                )
            )
