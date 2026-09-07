"""Render exact selected claims with bounded workers and a final access check."""

import asyncio
from uuid import UUID

from ase.application.dto import AccessClaims
from ase.application.ports.claim_evidence_package import ClaimEvidencePackageRenderer
from ase.application.reports.claim_export_selection import (
    ClaimExportReference,
    IdentityExportReference,
    RelationshipExportReference,
    SelectClaimExport,
)
from ase.application.reports.evidence_package import _PACKAGE_SLOTS
from ase.application.reports.original_assets import OriginalAssets
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.original_assets import OriginalAssetContent
from ase.domain.report_documents import ReportFile


class ExportClaimPackage:
    def __init__(
        self,
        selector: SelectClaimExport,
        renderer: ClaimEvidencePackageRenderer,
        original_assets: OriginalAssets | None = None,
    ) -> None:
        self.selector, self.renderer = selector, renderer
        self.original_assets = original_assets

    async def execute(
        self,
        actor: AccessClaims,
        report_id: UUID,
        number: int,
        references: tuple[ClaimExportReference, ...],
        *,
        identity_references: tuple[IdentityExportReference, ...] = (),
        relationship_references: tuple[RelationshipExportReference, ...] = (),
        asset_ids: tuple[UUID, ...] = (),
    ) -> ReportFile:
        if (
            not isinstance(asset_ids, tuple)
            or not isinstance(references, tuple)
            or not isinstance(identity_references, tuple)
            or not isinstance(relationship_references, tuple)
            or any(not isinstance(asset_id, UUID) for asset_id in asset_ids)
            or len(set(asset_ids)) != len(asset_ids)
            or not 1
            <= (
                len(references)
                + len(identity_references)
                + len(relationship_references)
                + len(asset_ids)
            )
            <= 20
        ):
            raise InvalidRequest("Select between one and twenty annotations or original assets.")
        # Admission bounds retained blobs as well as compression workers.
        if not _PACKAGE_SLOTS.acquire(blocking=False):
            raise RateLimited(5)
        task: asyncio.Task[bytes] | None = None
        try:
            assets: tuple[OriginalAssetContent, ...] = ()
            if asset_ids:
                if self.original_assets is None:
                    raise InvalidRequest("Original asset export is unavailable.")
                assets = await self.original_assets.select(actor, report_id, number, asset_ids)
            selected = (
                await self.selector.resolve(
                    actor,
                    report_id,
                    number,
                    references,
                    identity_references=identity_references,
                    relationship_references=relationship_references,
                    allow_empty=bool(asset_ids),
                )
                if relationship_references
                else (
                    await self.selector.resolve(
                        actor,
                        report_id,
                        number,
                        references,
                        identity_references=identity_references,
                        allow_empty=True,
                    )
                    if asset_ids
                    else (
                        await self.selector.resolve(
                            actor,
                            report_id,
                            number,
                            references,
                            identity_references=identity_references,
                        )
                        if identity_references
                        else await self.selector.resolve(actor, report_id, number, references)
                    )
                )
            )

            def render() -> bytes:
                if selected.relationship_revisions:
                    return self.renderer.render(
                        selected.record,
                        selected.version,
                        selected.revisions,
                        identity_revisions=selected.identity_revisions,
                        relationship_revisions=selected.relationship_revisions,
                        original_assets=assets,
                    )
                if assets:
                    return self.renderer.render(
                        selected.record,
                        selected.version,
                        selected.revisions,
                        identity_revisions=selected.identity_revisions,
                        original_assets=assets,
                    )
                if selected.identity_revisions:
                    return self.renderer.render(
                        selected.record,
                        selected.version,
                        selected.revisions,
                        identity_revisions=selected.identity_revisions,
                    )
                return self.renderer.render(selected.record, selected.version, selected.revisions)

            # A cancelled request cannot stop compression. Retain its admission slot
            # until the worker ends, without allowing that worker to access the DB.
            task = asyncio.create_task(asyncio.to_thread(render))
            task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
            content = await asyncio.shield(task)
            await self.selector.recheck(actor, selected)
            if assets and self.original_assets is not None:
                await self.original_assets.recheck(actor, assets)
            return ReportFile(
                content,
                "application/zip",
                f"evidence-{report_id}-v{number}-selected-originals.zip"
                if assets
                else f"evidence-{report_id}-v{number}-selected-annotations.zip"
                if selected.identity_revisions or selected.relationship_revisions
                else f"evidence-{report_id}-v{number}-selected-claims.zip",
            )
        finally:
            # Cancellation cannot stop a running compression thread. Transfer
            # admission ownership to its shielded task until actual completion.
            if task is not None and not task.done():
                task.add_done_callback(lambda _: _PACKAGE_SLOTS.release())
            else:
                _PACKAGE_SLOTS.release()
