"""Original asset reservations and byte lifecycle within the caller's transaction."""

from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.models import ReportVersionRow
from ase.adapters.persistence.original_asset_models import OriginalAssetRow as Row
from ase.domain.original_assets import AssetStatus, OriginalAsset, OriginalAssetContent

LIVE = ("reserved", "uploading", "active")
PENDING = ("reserved", "uploading")


def _asset(row: Row) -> OriginalAsset:
    return OriginalAsset(
        row.id,
        row.report_id,
        row.report_version_id,
        row.version_number,
        row.evidence_label,
        row.source_id,
        row.event_id,
        row.sha256,
        row.byte_count,
        row.filename,
        row.media_type,
        row.permitted_use,
        row.owner_id,
        row.team_id,
        row.uploader_id,
        row.created_at,
        row.expires_at,
        row.reservation_expires_at,
        cast(AssetStatus, row.status),
        row.transitioned_at,
        row.session_family_id,
    )


def _scrub(status: str, now: datetime) -> dict[str, Any]:
    return {
        "status": status,
        "transitioned_at": now,
        "content": None,
        "byte_count": 0,
        "evidence_label": "",
        "source_id": "",
        "event_id": "",
        "sha256": "",
        "filename": "",
        "media_type": "",
        "permitted_use": "",
        "session_family_id": None,
    }


class SqlOriginalAssetRepository:
    """Metadata reads never select blob bytes; writes do not commit independently."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def expire(self, now: datetime) -> None:
        await self.session.execute(
            delete(Row).where(
                Row.status.in_(("deleted", "expired")),
                Row.transitioned_at <= now - timedelta(days=30),
            )
        )
        await self.session.execute(
            update(Row)
            .where(
                Row.status.in_(LIVE),
                or_(
                    Row.expires_at <= now,
                    and_(Row.status.in_(PENDING), Row.reservation_expires_at <= now),
                ),
            )
            .values(**_scrub("expired", now))
            .execution_options(synchronize_session=False)
        )

    async def usage(
        self, owner_id: UUID | None = None, team_id: UUID | None = None
    ) -> tuple[int, int]:
        query = select(func.count(Row.id), func.coalesce(func.sum(Row.byte_count), 0))
        if team_id is not None:
            query = query.where(Row.team_id == team_id)
        elif owner_id is not None:
            query = query.where(Row.team_id.is_(None), Row.owner_id == owner_id)
        count, size = (await self.session.execute(query)).one()
        return int(count), int(size)

    async def pending_count(self) -> int:
        return int(
            await self.session.scalar(select(func.count(Row.id)).where(Row.status.in_(PENDING)))
            or 0
        )

    async def create(self, asset: OriginalAsset) -> None:
        if asset.status != "reserved":
            raise ValueError("Original assets must begin with a reservation")
        anchor = await self.session.scalar(
            select(ReportVersionRow.id).where(
                ReportVersionRow.id == asset.report_version_id,
                ReportVersionRow.report_id == asset.report_id,
                ReportVersionRow.number == asset.version_number,
            )
        )
        if anchor is None:
            raise ValueError("Original asset requires its exact parent report version")
        self.session.add(Row(**asdict(asset), content=None))
        await self.session.flush()

    async def get(self, asset_id: UUID) -> OriginalAsset | None:
        row = await self.session.get(Row, asset_id, populate_existing=True)
        return _asset(row) if row else None

    async def list(self, report_id: UUID, version_number: int) -> tuple[OriginalAsset, ...]:
        rows = await self.session.scalars(
            select(Row)
            .where(
                Row.report_id == report_id,
                Row.version_number == version_number,
                Row.status.in_(LIVE),
            )
            .order_by(Row.created_at, Row.id)
            .limit(4096)
            .execution_options(populate_existing=True)
        )
        return tuple(_asset(row) for row in rows)

    async def begin_upload(self, asset_id: UUID, now: datetime) -> bool:
        result = await self.session.scalar(
            update(Row)
            .where(
                Row.id == asset_id,
                Row.status == "reserved",
                Row.reservation_expires_at > now,
                Row.expires_at > now,
            )
            .values(status="uploading", reservation_expires_at=now + timedelta(minutes=2))
            .returning(Row.id)
            .execution_options(synchronize_session=False)
        )
        return result is not None

    async def activate(self, asset_id: UUID, content: bytes, now: datetime) -> bool:
        result = await self.session.scalar(
            update(Row)
            .where(
                Row.id == asset_id,
                Row.status == "uploading",
                Row.reservation_expires_at > now,
                Row.expires_at > now,
                Row.byte_count == len(content),
            )
            .values(status="active", content=content, transitioned_at=now)
            .returning(Row.id)
            .execution_options(synchronize_session=False)
        )
        return result is not None

    async def content(self, asset_id: UUID) -> OriginalAssetContent | None:
        row = await self.session.execute(
            select(Row, Row.content)
            .where(
                Row.id == asset_id,
                Row.status == "active",
            )
            .execution_options(populate_existing=True)
        )
        result = row.one_or_none()
        return OriginalAssetContent(_asset(result[0]), result[1]) if result else None

    async def delete(self, asset_id: UUID, now: datetime) -> None:
        await self.session.execute(
            update(Row)
            .where(Row.id == asset_id, Row.status.in_(LIVE))
            .values(**_scrub("deleted", now))
            .execution_options(synchronize_session=False)
        )

    async def delete_for_report(self, report_id: UUID) -> None:
        await self.session.execute(delete(Row).where(Row.report_id == report_id))
