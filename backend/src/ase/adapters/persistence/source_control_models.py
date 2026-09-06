"""Small persisted source activation overrides, without credentials or raw events."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class SourceControlRow(Base):
    __tablename__ = "source_controls"

    source_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
