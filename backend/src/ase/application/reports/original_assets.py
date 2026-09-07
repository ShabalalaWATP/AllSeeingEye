"""Original retention with transactional admission and fresh authority after byte intake."""

import hashlib
from datetime import timedelta
from uuid import UUID, uuid4

from ase.application.access import AccessContext, AccessPolicy
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims
from ase.application.ports import Clock, RefreshTokenRepository, UnitOfWork, UserRepository
from ase.application.ports.original_assets import OriginalAssetRepository
from ase.application.ports.reports import ReportRepository
from ase.application.reports.original_asset_anchor import original_anchor, validate_request
from ase.domain.errors import Conflict, InvalidRequest, NotFound, RateLimited, Unauthenticated
from ase.domain.original_assets import (
    MAX_EXPORT_ASSET_BYTES,
    MAX_GLOBAL_BYTES,
    MAX_GLOBAL_RECORDS,
    MAX_PENDING_UPLOADS,
    MAX_PERSONAL_BYTES,
    MAX_PERSONAL_RECORDS,
    MAX_SELECTED_ASSETS,
    MAX_TEAM_BYTES,
    MAX_TEAM_RECORDS,
    OriginalAsset,
    OriginalAssetContent,
    OriginalAssetRequest,
)
from ase.domain.report_records import ReportRecord, ReportVersion


class OriginalAssets:
    def __init__(
        self,
        users: UserRepository,
        refresh: RefreshTokenRepository,
        reports: ReportRepository,
        assets: OriginalAssetRepository,
        access: AccessPolicy,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self.users, self.refresh, self.reports, self.assets = users, refresh, reports, assets
        self.access, self.clock, self.uow = access, clock, uow

    async def _context(self, claims: AccessClaims) -> AccessContext:
        await self.users.lock_administration()
        await self.users.lock_by_id(claims.user_id)
        actor = await validate_current_session(claims, self.users, self.refresh, self.clock)
        await self.assets.expire(self.clock.now())
        return await self.access.context(actor)

    async def _report(
        self,
        access: AccessContext,
        report_id: UUID,
        number: int,
        *,
        write: bool = False,
    ) -> tuple[ReportRecord, ReportVersion]:
        report = await self.reports.get(report_id)
        if report is None:
            raise NotFound()
        if write:
            access.require_write(report.created_by, report.team_id)
        else:
            access.require_read(report.created_by, report.team_id)
        version = await self.reports.get_version(report_id, number)
        if version is None:
            raise NotFound()
        return report, version

    async def _asset(
        self,
        access: AccessContext,
        report_id: UUID,
        asset_id: UUID,
        *,
        write: bool = False,
    ) -> OriginalAsset:
        asset = await self.assets.get(asset_id)
        if asset is None or asset.report_id != report_id:
            raise NotFound()
        report, version = await self._report(access, report_id, asset.version_number, write=write)
        if asset.report_version_id != version.id:
            raise Conflict("The original's frozen report version has changed.")
        access.require_same_scope(asset.owner_id, asset.team_id, report.created_by, report.team_id)
        if asset.status in {"deleted", "expired"}:
            raise NotFound()
        item, digest, filename, media_type = original_anchor(version, asset.evidence_label)
        if (asset.sha256, asset.filename, asset.media_type, asset.source_id, asset.event_id) != (
            digest,
            filename,
            media_type,
            item.source_id,
            item.event_id,
        ):
            raise Conflict("The original's frozen evidence anchor has changed.")
        return asset

    async def _quota(self, owner: UUID, team: UUID | None, additional: int, count: int) -> None:
        for personal, scope, max_count, max_bytes in (
            (None, None, MAX_GLOBAL_RECORDS, MAX_GLOBAL_BYTES),
            (
                owner,
                team,
                MAX_TEAM_RECORDS if team else MAX_PERSONAL_RECORDS,
                MAX_TEAM_BYTES if team else MAX_PERSONAL_BYTES,
            ),
        ):
            used_count, used_bytes = await self.assets.usage(personal, scope)
            if used_count + count > max_count or used_bytes + additional > max_bytes:
                raise InvalidRequest("Original retention has reached its storage or record limit.")

    async def reserve(
        self,
        claims: AccessClaims,
        report_id: UUID,
        request: OriginalAssetRequest,
    ) -> OriginalAsset:
        validate_request(request)
        access = await self._context(claims)
        report, version = await self._report(access, report_id, request.version_number, write=True)
        item, digest, filename, media_type = original_anchor(version, request.evidence_label)
        if request.media_type != media_type:
            raise InvalidRequest("The declared media type differs from the frozen original.")
        if await self.assets.pending_count() >= MAX_PENDING_UPLOADS:
            raise RateLimited(60)
        await self._quota(report.created_by, report.team_id, request.byte_count, 1)
        now = self.clock.now()
        asset = OriginalAsset(
            uuid4(),
            report.id,
            version.id,
            version.number,
            item.label,
            item.source_id,
            item.event_id,
            digest,
            request.byte_count,
            filename,
            media_type,
            request.permitted_use,
            report.created_by,
            report.team_id,
            access.actor.id,
            now,
            now + timedelta(days=request.retention_days),
            now + timedelta(minutes=2),
            session_family_id=claims.family_id,
        )
        await self.assets.create(asset)
        await self.uow.commit()
        return asset

    async def list(
        self,
        claims: AccessClaims,
        report_id: UUID,
        number: int,
    ) -> tuple[OriginalAsset, ...]:
        access = await self._context(claims)
        await self._report(access, report_id, number)
        assets = await self.assets.list(report_id, number)
        await self.uow.commit()
        return assets

    async def begin_upload(
        self,
        claims: AccessClaims,
        report_id: UUID,
        asset_id: UUID,
    ) -> OriginalAsset:
        access = await self._context(claims)
        asset = await self._asset(access, report_id, asset_id, write=True)
        if asset.uploader_id != access.actor.id or asset.session_family_id != claims.family_id:
            raise NotFound()
        if not await self.assets.begin_upload(asset.id, self.clock.now()):
            raise Conflict("This upload reservation is no longer available.")
        await self.uow.commit()
        return asset

    async def finish_upload(
        self,
        claims: AccessClaims,
        report_id: UUID,
        asset_id: UUID,
        content: bytes,
    ) -> OriginalAsset:
        access = await self._context(claims)
        asset = await self._asset(access, report_id, asset_id, write=True)
        if asset.uploader_id != access.actor.id or asset.session_family_id != claims.family_id:
            raise NotFound()
        if len(content) != asset.byte_count or hashlib.sha256(content).hexdigest() != asset.sha256:
            raise InvalidRequest("These bytes do not match the original frozen SHA-256 and size.")
        await self._quota(asset.owner_id, asset.team_id, 0, 0)
        if not await self.assets.activate(asset.id, content, self.clock.now()):
            raise Conflict("This upload reservation has expired or changed.")
        saved = await self.assets.get(asset.id)
        if saved is None:
            raise Conflict("The upload reservation disappeared before retention completed.")
        await self.uow.commit()
        return saved

    async def abandon_upload(self, asset_id: UUID, uploader_id: UUID) -> None:
        """Internal failure cleanup only; cannot delete a successfully retained original."""
        await self.users.lock_administration()
        asset = await self.assets.get(asset_id)
        if asset and asset.uploader_id == uploader_id and asset.status in {"reserved", "uploading"}:
            await self.assets.delete(asset.id, self.clock.now())
        await self.uow.commit()

    async def delete(self, claims: AccessClaims, report_id: UUID, asset_id: UUID) -> None:
        access = await self._context(claims)
        asset = await self._asset(access, report_id, asset_id, write=True)
        await self.assets.delete(asset.id, self.clock.now())
        await self.uow.commit()

    async def select(
        self,
        claims: AccessClaims,
        report_id: UUID,
        version_number: int,
        asset_ids: tuple[UUID, ...],
    ) -> tuple[OriginalAssetContent, ...]:
        if not 1 <= len(asset_ids) <= MAX_SELECTED_ASSETS or len(set(asset_ids)) != len(asset_ids):
            raise InvalidRequest("Choose one to twenty distinct original asset IDs.")
        access = await self._context(claims)
        await self._report(access, report_id, version_number)
        results: list[OriginalAssetContent] = []
        total = 0
        for asset_id in asset_ids:
            asset = await self._asset(access, report_id, asset_id)
            if asset.version_number != version_number or asset.status != "active":
                raise NotFound()
            total += asset.byte_count
            if total > MAX_EXPORT_ASSET_BYTES:
                raise InvalidRequest("Selected originals exceed the 24 MiB export limit.")
            found = await self.assets.content(asset.id)
            if (
                found is None
                or len(found.content) != asset.byte_count
                or (hashlib.sha256(found.content).hexdigest() != asset.sha256)
            ):
                raise Conflict("The retained original failed its integrity check.")
            results.append(OriginalAssetContent(asset, found.content))
        await self.uow.commit()
        return tuple(results)

    async def recheck(
        self, claims: AccessClaims, selected: tuple[OriginalAssetContent, ...]
    ) -> None:
        access = await self._context(claims)
        for row in selected:
            current = await self._asset(access, row.asset.report_id, row.asset.id)
            if current != row.asset or current.status != "active":
                raise Conflict("A selected original expired, changed or was deleted during export.")
        await self.uow.commit()

        if any(row.asset.expires_at <= self.clock.now() for row in selected):
            raise NotFound()
        if claims.expires_at <= self.clock.now():
            raise Unauthenticated()

    async def download(
        self,
        claims: AccessClaims,
        report_id: UUID,
        asset_id: UUID,
    ) -> OriginalAssetContent:
        access = await self._context(claims)
        asset = await self._asset(access, report_id, asset_id)
        await self.uow.commit()
        selected = await self.select(claims, report_id, asset.version_number, (asset_id,))
        await self.recheck(claims, selected)
        return selected[0]
