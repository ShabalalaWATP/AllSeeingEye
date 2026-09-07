"""Database rows for bounded original bytes and scrubbed lifecycle tombstones."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, LargeBinary, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class OriginalAssetRow(Base):
    __tablename__ = "original_assets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('reserved','uploading','active','deleted','expired')",
            name="ck_original_asset_status",
        ),
        CheckConstraint("byte_count >= 0 AND byte_count <= 8388608", name="ck_original_asset_size"),
        CheckConstraint("version_number > 0", name="ck_original_asset_version"),
        CheckConstraint(
            "(status = 'active' AND content IS NOT NULL "
            "AND length(content) = byte_count AND byte_count > 0) "
            "OR (status IN ('reserved','uploading') AND content IS NULL AND byte_count > 0) "
            "OR (status IN ('deleted','expired') AND content IS NULL AND byte_count = 0)",
            name="ck_original_asset_content",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), index=True
    )
    report_version_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("report_versions.id", ondelete="CASCADE")
    )
    version_number: Mapped[int] = mapped_column(Integer)
    evidence_label: Mapped[str] = mapped_column(String(64))
    source_id: Mapped[str] = mapped_column(String(128))
    event_id: Mapped[str] = mapped_column(String(256))
    sha256: Mapped[str] = mapped_column(String(64))
    byte_count: Mapped[int] = mapped_column(Integer)
    filename: Mapped[str] = mapped_column(String(240))
    media_type: Mapped[str] = mapped_column(String(160))
    permitted_use: Mapped[str] = mapped_column(String(2000))
    owner_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"), index=True)
    uploader_id: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    reservation_expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String(16), index=True)
    transitioned_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    session_family_id: Mapped[UUID | None] = mapped_column(Uuid)
    content: Mapped[bytes | None] = mapped_column(LargeBinary, deferred=True)
