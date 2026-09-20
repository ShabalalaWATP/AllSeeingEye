"""SQL workspace documents with scope filtering before pagination and compare-and-swap."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Uuid,
    and_,
    delete,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.access import visibility_predicate
from ase.adapters.persistence.base import Base, UTCDateTime
from ase.domain.access import Visibility
from ase.domain.map_workspace import MapWorkspaceDocument, WorkspaceKind


class MapWorkspaceRow(Base):
    __tablename__ = "map_workspace_documents"
    __table_args__ = (CheckConstraint("revision > 0", name="ck_map_workspace_revision"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    kind: Mapped[WorkspaceKind] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[UUID] = mapped_column(Uuid, index=True)
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


def _document(row: MapWorkspaceRow) -> MapWorkspaceDocument:
    return MapWorkspaceDocument(
        row.id,
        row.kind,
        row.title,
        row.payload,
        row.revision,
        row.created_by,
        row.team_id,
        row.created_at,
        row.updated_at,
    )


class SqlMapWorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, document_id: UUID) -> MapWorkspaceDocument | None:
        row = await self.session.get(MapWorkspaceRow, document_id, populate_existing=True)
        return _document(row) if row else None

    async def list_visible(
        self, visibility: Visibility, kind: WorkspaceKind, limit: int, offset: int
    ) -> list[MapWorkspaceDocument]:
        rows = await self.session.scalars(
            select(MapWorkspaceRow)
            .where(
                MapWorkspaceRow.kind == kind,
                visibility_predicate(
                    MapWorkspaceRow.created_by, MapWorkspaceRow.team_id, visibility
                ),
            )
            .order_by(MapWorkspaceRow.updated_at.desc(), MapWorkspaceRow.id)
            .limit(limit)
            .offset(offset)
        )
        return [_document(row) for row in rows]

    async def scope_count(self, owner: UUID, team_id: UUID | None) -> int:
        scope = (
            MapWorkspaceRow.team_id == team_id
            if team_id
            else and_(MapWorkspaceRow.team_id.is_(None), MapWorkspaceRow.created_by == owner)
        )
        return int(
            await self.session.scalar(
                select(func.count()).select_from(MapWorkspaceRow).where(scope)
            )
            or 0
        )

    async def create(self, document: MapWorkspaceDocument) -> None:
        self.session.add(
            MapWorkspaceRow(
                **{field: getattr(document, field) for field in document.__dataclass_fields__}
            )
        )
        await self.session.flush()

    async def update(self, document: MapWorkspaceDocument, expected_revision: int) -> bool:
        changed = await self.session.scalar(
            update(MapWorkspaceRow)
            .where(
                MapWorkspaceRow.id == document.id,
                MapWorkspaceRow.revision == expected_revision,
            )
            .values(
                title=document.title,
                payload=document.payload,
                revision=document.revision,
                updated_at=document.updated_at,
            )
            .returning(MapWorkspaceRow.id)
            .execution_options(synchronize_session=False)
        )
        return changed is not None

    async def remove(self, document_id: UUID) -> None:
        await self.session.execute(delete(MapWorkspaceRow).where(MapWorkspaceRow.id == document_id))
