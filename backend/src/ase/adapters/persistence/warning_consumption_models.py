"""One compact, bounded consumed-identity record per warning rule."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, LargeBinary, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class WarningConsumptionRow(Base):
    __tablename__ = "warning_consumption"
    __table_args__ = (
        CheckConstraint("count >= 0 AND count <= 350000", name="ck_warning_consumed_count"),
    )

    indicator_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("indicators.id", ondelete="CASCADE"),
        primary_key=True,
    )
    data: Mapped[bytes] = mapped_column(LargeBinary)
    count: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True, index=True)
    legacy_before: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
