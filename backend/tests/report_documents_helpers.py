"""Frozen report fixtures for document exports and version comparisons."""

from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

from ase.application.reports.render import render_markdown
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
    markdown = render_markdown(
        record.header, body, evidence, quality, findings, direction=direction, advocacy=advocacy
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
        markdown,
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
    return record, version
