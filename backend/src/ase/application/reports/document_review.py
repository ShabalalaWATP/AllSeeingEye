"""Concise frozen assessment concerns for the canonical report product."""

from __future__ import annotations

from ase.application.reports.document_builder import DocumentBuilder
from ase.application.reports.export_text import review_notice
from ase.application.reports.quality_gate import material_review_reasons
from ase.domain.citation_checks import CitationStatus
from ase.domain.report_documents import BlockKind
from ase.domain.report_records import ReportVersion
from ase.domain.reports import ReportStatus


def opening_review_notice(doc: DocumentBuilder, version: ReportVersion) -> None:
    if version.status is not ReportStatus.READY:
        doc.add(review_notice(version.status), BlockKind.WARNING)
        if version.status is ReportStatus.NEEDS_REVIEW:
            for reason in material_review_reasons(
                version.assessment, version.citation_checks, version.challenge
            ):
                doc.add(reason, BlockKind.WARNING)


def judgement_review(doc: DocumentBuilder, version: ReportVersion, judgement_id: str) -> None:
    """Show issues beside the affected judgement, not only in a technical workspace."""
    checks = version.citation_checks
    if checks is not None:
        for row in checks.judgements:
            if row.judgement_id != judgement_id:
                continue
            if row.status is CitationStatus.REVIEW_REQUIRED:
                labels = ", ".join(
                    dict.fromkeys(
                        citation.label
                        for citation in row.citations
                        if citation.status is CitationStatus.REVIEW_REQUIRED
                    )
                )
                doc.add(
                    f"Citation review: source wording for {labels or 'this judgement'} "
                    "has literal differences that need an analyst's assessment. "
                    "The excerpt check does not establish factual support.",
                    BlockKind.WARNING,
                )
            elif row.status is CitationStatus.ABSENT:
                doc.add(
                    "Citation review: supporting frozen source context is missing for "
                    "this judgement. Its claim has not been substantiated by the excerpt check.",
                    BlockKind.WARNING,
                )
            elif row.status is CitationStatus.CONTEXT_INSUFFICIENT:
                doc.add(
                    "Citation context is limited for this judgement; the excerpt check "
                    "cannot establish whether the cited source supports it.",
                    BlockKind.WARNING,
                )
            break
    challenge = version.challenge
    if challenge is None:
        return
    for review in challenge.reviews:
        if review.judgement_id != judgement_id:
            continue
        if review.status == "completed" and review.advocacy is not None:
            argument = review.advocacy.argument.strip()
            rationale = review.advocacy.rationale.strip()
            doc.cited(
                f"Alternative view to test (unverified): {argument} {rationale}".strip(),
                review.advocacy.evidence,
            )
        elif review.status != "completed":
            doc.add(
                "The planned challenge of this judgement was not completed; "
                "absence of counterevidence cannot be inferred.",
                BlockKind.WARNING,
            )
        break
