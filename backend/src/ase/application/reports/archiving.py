"""Preserve what a report cites: ask the archiver for a snapshot of each cited URL.

Runs after the version is stored. The archive addresses are written onto the frozen
evidence and the Markdown is rendered again so the export carries them too.
"""

from __future__ import annotations

from dataclasses import replace

from ase.application.ports import UnitOfWork
from ase.application.ports.archive import Archiver
from ase.application.ports.reports import ReportRepository
from ase.application.reports.export_text import safe_url
from ase.application.reports.frozen_header import frozen_period_line
from ase.application.reports.render import render_markdown
from ase.domain.evidence import EvidenceItem
from ase.domain.report_records import ReportVersion


def archivable(item: EvidenceItem) -> bool:
    return bool(item.url) and item.archive_url is None and safe_url(item.url) is not None


async def archive_evidence(
    archiver: Archiver, reports: ReportRepository, uow: UnitOfWork, version: ReportVersion
) -> int:
    """Archive every cited item that can be archived; the number of snapshots is returned."""
    record = await reports.get(version.report_id)
    if record is None:
        return 0
    cited = version.body.cited_labels() | frozenset(
        version.advocacy.evidence if version.advocacy else ()
    )
    archives: dict[str, str] = {}
    for item in version.evidence:
        if item.label not in cited or not archivable(item) or item.url is None:
            continue
        snapshot = await archiver.archive(item.url, item.published_at)
        if snapshot:
            archives[item.label] = snapshot
    if not archives:
        return 0
    evidence = tuple(
        replace(item, archive_url=archives.get(item.label, item.archive_url))
        for item in version.evidence
    )
    requirements = version.direction.requirement_ids() if version.direction else ()
    markdown = render_markdown(
        replace(record.header, requirements=requirements),
        version.body,
        evidence,
        version.quality,
        version.findings,
        direction=version.direction,
        advocacy=version.advocacy,
        status=version.status,
        assessment=version.assessment,
        period_line=frozen_period_line(record, version),
    )
    await reports.set_archives(version.id, archives, markdown)
    await uow.commit()
    return len(archives)
