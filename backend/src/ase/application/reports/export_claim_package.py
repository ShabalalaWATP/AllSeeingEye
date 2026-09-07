"""Render exact selected claims with bounded workers and a final access check."""

import asyncio
from uuid import UUID

from ase.application.dto import AccessClaims
from ase.application.ports.claim_evidence_package import ClaimEvidencePackageRenderer
from ase.application.reports.claim_export_selection import (
    ClaimExportReference,
    IdentityExportReference,
    SelectClaimExport,
)
from ase.application.reports.evidence_package import _PACKAGE_SLOTS
from ase.domain.errors import RateLimited
from ase.domain.report_documents import ReportFile


class ExportClaimPackage:
    def __init__(self, selector: SelectClaimExport, renderer: ClaimEvidencePackageRenderer) -> None:
        self.selector, self.renderer = selector, renderer

    async def execute(
        self,
        actor: AccessClaims,
        report_id: UUID,
        number: int,
        references: tuple[ClaimExportReference, ...],
        *,
        identity_references: tuple[IdentityExportReference, ...] = (),
    ) -> ReportFile:
        selected = (
            await self.selector.resolve(
                actor, report_id, number, references, identity_references=identity_references
            )
            if identity_references
            else await self.selector.resolve(actor, report_id, number, references)
        )
        # Both package routes share the same process-wide compression allowance.
        if not _PACKAGE_SLOTS.acquire(blocking=False):
            raise RateLimited(5)

        def render() -> bytes:
            try:
                if selected.identity_revisions:
                    return self.renderer.render(
                        selected.record,
                        selected.version,
                        selected.revisions,
                        identity_revisions=selected.identity_revisions,
                    )
                return self.renderer.render(selected.record, selected.version, selected.revisions)
            finally:
                _PACKAGE_SLOTS.release()

        # A cancelled request cannot stop compression. Retain its admission slot
        # until the worker ends, without allowing that worker to access the DB.
        task = asyncio.create_task(asyncio.to_thread(render))
        task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        content = await asyncio.shield(task)
        await self.selector.recheck(actor, selected)
        return ReportFile(
            content,
            "application/zip",
            f"evidence-{report_id}-v{number}-selected-annotations.zip"
            if selected.identity_revisions
            else f"evidence-{report_id}-v{number}-selected-claims.zip",
        )
