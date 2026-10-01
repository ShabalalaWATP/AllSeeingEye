"""Frozen report fixtures for document exports and version comparisons."""

import io
import zipfile
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from ase.adapters.reports.evidence_package import FrozenEvidencePackageRenderer
from ase.adapters.reports.markdown_package import render_markdown_export
from ase.application.reports.document import build_document
from ase.application.reports.publication_markdown import render_document_markdown
from ase.application.reports.selection import select_evidence
from ase.application.reports.templates import TEMPLATES
from ase.domain.advocacy import DevilsAdvocacy
from ase.domain.direction import Direction
from ase.domain.doctrine import Confidence
from ase.domain.evidence import quality_of_information
from ase.domain.report_records import ReportRecord, ReportVersion
from ase.domain.reports import ReportStatus, parse_body
from ase.domain.validation import Finding, Severity
from feeds_helpers import NOW
from report_helpers import filled_store, good_body


def canonical_markdown(record: ReportRecord, version: ReportVersion) -> str:
    """The Markdown that generation, archiving and download produce for this version."""
    return render_document_markdown(build_document(record, version))


def downloaded_markdown(record: ReportRecord, version: ReportVersion) -> str:
    """The Markdown a reader downloads, through the same path as the export endpoint."""
    export = render_markdown_export(
        build_document(record, version), record.id, version.id, version.number
    )
    return export.content.decode("utf-8")


def package_file(record: ReportRecord, version: ReportVersion, name: str) -> bytes:
    """One file of the frozen evidence package: the supporting data beside the reader product."""
    package = FrozenEvidencePackageRenderer().render(record, version)
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        return archive.read(name)


def document_records(owner: UUID | None = None) -> tuple[ReportRecord, ReportVersion]:
    record = ReportRecord(
        uuid4(),
        "intsum",
        "Intelligence summary: Ukraine",
        {},
        NOW - timedelta(days=2),
        NOW,
        NOW,
        ReportStatus.NEEDS_REVIEW,
        owner or uuid4(),
        NOW,
        1,
    )
    evidence = select_evidence(filled_store(), {}, TEMPLATES["intsum"].strategy, now=NOW).items
    evidence = (
        replace(
            evidence[0],
            summary="Frozen report source detail.",
            url="https://example.org/report",
            archive_url="https://web.archive.org/web/20260901/https://example.org/report",
            flags=("instruction-like text",),
        ),
        *evidence[1:],
    )
    body = parse_body(good_body())
    quality = quality_of_information(evidence)
    findings = (Finding("citation", Severity.WARNING, "KJ2", "Review the contradictory source."),)
    direction = Direction("What is changing?", ("Where?",), ("Road use",), ("Ukraine",))
    advocacy = DevilsAdvocacy(
        "KJ1",
        "A pause remains possible.",
        ("E1",),
        True,
        "Evidence is limited.",
        Confidence.HIGH,
        Confidence.MODERATE,
    )
    version = ReportVersion(
        uuid4(),
        record.id,
        1,
        ReportStatus.NEEDS_REVIEW,
        body,
        findings,
        evidence,
        quality,
        "",
        None,
        "local-test-model",
        50,
        30,
        80,
        1,
        NOW,
        direction,
        advocacy,
    )
    # Generated through the canonical path, as production does; the version keeps no typed
    # period, so the document states that its period was not captured.
    version.markdown = canonical_markdown(record, version)
    return record, version


# Markdown saved by the retired generator, captured once from its output. Saved versions
# keep their Markdown verbatim, so it must stay readable without that generator.
LEGACY_MARKDOWN = (Path(__file__).parent / "fixtures" / "legacy_report_markdown.md").read_text(
    encoding="utf-8"
)


def legacy_records(owner: UUID | None = None) -> tuple[ReportRecord, ReportVersion]:
    """A version saved before typed periods: only its old Markdown holds the frozen period."""
    record, version = document_records(owner)
    record.template = "country_brief"
    return record, replace(
        version, markdown=LEGACY_MARKDOWN, period_from=None, period_to=None, data_cutoff=None
    )
