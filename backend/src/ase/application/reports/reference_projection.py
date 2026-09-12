"""Build safe, deterministic references from frozen evidence."""

from collections.abc import Mapping
from datetime import UTC, datetime

from ase.application.reports.export_text import safe_url
from ase.domain.evidence import EvidenceItem
from ase.domain.report_documents import DocumentReference


def _date(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).date().isoformat() if value.tzinfo else value.date().isoformat()


def _reference_date(item: EvidenceItem) -> str | None:
    """Use a resolved declared source date when no publication timestamp exists."""
    published = _date(item.published_at)
    if published is not None:
        return published
    ordered = sorted(
        item.source_dates,
        key=lambda row: (
            0 if row.role == "publication" else 1,
            0 if row.role == "occurrence" else 1,
        ),
    )
    for source_date in ordered:
        if source_date.status != "resolved":
            continue
        if source_date.value is not None:
            return _date(source_date.value)
        if source_date.day_start is not None:
            return source_date.day_start.isoformat()
    return None


def build_references(
    numbers: Mapping[str, int], evidence: Mapping[str, EvidenceItem]
) -> tuple[DocumentReference, ...]:
    return tuple(
        DocumentReference(
            number=number,
            evidence_label=label,
            title=evidence[label].title_en or evidence[label].title,
            publisher=evidence[label].source_name,
            published_at=_reference_date(evidence[label]),
            accessed_at=evidence[label].captured_at.isoformat(),
            url=safe_url(evidence[label].url),
            archive_url=safe_url(evidence[label].archive_url),
            original_title=evidence[label].title if evidence[label].title_en else None,
            language=evidence[label].language,
        )
        for label, number in sorted(numbers.items(), key=lambda item: item[1])
    )


def reference_text(reference: DocumentReference) -> str:
    date = reference.published_at or "date not reported"
    original = f" Original title: {reference.original_title}." if reference.original_title else ""
    links = ""
    if reference.url:
        links += f" Source: {reference.url}."
    if reference.archive_url:
        links += f" Archived copy: {reference.archive_url}."
    return (
        f"[{reference.number}] {reference.publisher}. {reference.title}.{original} {date}.{links} "
        f"Accessed {reference.accessed_at}."
    )
