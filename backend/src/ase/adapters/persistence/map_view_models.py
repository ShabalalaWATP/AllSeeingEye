"""Saved-map roots and append-only revisions; lifecycle changes affect roots only."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class MapViewRow(Base):
    __tablename__ = "map_views"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    report_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("reports.id"), index=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, index=True)
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"), index=True)
    # No cyclic foreign key: repository writes the pointer and revision in one transaction.
    latest_revision_id: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class MapViewRevisionRow(Base):
    __tablename__ = "map_view_revisions"
    __table_args__ = (
        UniqueConstraint("view_id", "number", name="uq_map_view_revision_number"),
        CheckConstraint("number > 0", name="ck_map_view_revision_number"),
        CheckConstraint("byte_size > 0", name="ck_map_view_revision_bytes"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    view_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("map_views.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    report_version_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("report_versions.id"))
    report_version_number: Mapped[int] = mapped_column(Integer)
    state: Mapped[dict[str, Any]] = mapped_column(JSON)
    evidence_sha256: Mapped[str] = mapped_column(String(64))
    content_sha256: Mapped[str] = mapped_column(String(64))
    byte_size: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
