"""User-owned report annotations with cascading normalised tags."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, ForeignKeyConstraint, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class ResearchLibraryRow(Base):
    __tablename__ = "research_library"
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    report_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )
    favourite: Mapped[bool] = mapped_column(Boolean, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)


class ResearchLibraryTagRow(Base):
    __tablename__ = "research_library_tags"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id", "report_id"],
            ["research_library.user_id", "research_library.report_id"],
            ondelete="CASCADE",
        ),
    )
    user_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    report_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    tag: Mapped[str] = mapped_column(String(40), primary_key=True)
