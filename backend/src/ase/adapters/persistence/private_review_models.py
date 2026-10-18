"""Owner-scoped removal decisions and permanent identity tombstone markers."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class PrivateDataReviewRow(Base):
    __tablename__ = "private_data_reviews"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_private_review_revision"),
        CheckConstraint(
            "decision IN ('retain','hold','remove')", name="ck_private_review_decision"
        ),
        CheckConstraint(
            "purpose IN ('quarterly','account_closure','rights_request','purpose_complete')",
            name="ck_private_review_purpose",
        ),
        CheckConstraint("next_review_at > reviewed_at", name="ck_private_review_dates"),
    )

    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer)
    decision: Mapped[str] = mapped_column(String(12))
    purpose: Mapped[str] = mapped_column(String(24))
    reviewed_by: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime)
    next_review_at: Mapped[datetime] = mapped_column(UTCDateTime)
    erased_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
