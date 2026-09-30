"""Small monthly reservation projections; checkpoint calls remain the audit record."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class ReportJobUsageRow(Base):
    __tablename__ = "report_job_monthly_usage"
    __table_args__ = (
        Index("ix_report_job_usage_owner_month", "owner_id", "month"),
        CheckConstraint(
            "owner_requests >= 0 AND owner_output_tokens >= 0 AND "
            "subscription_requests >= 0 AND subscription_output_tokens >= 0",
            name="ck_report_job_usage_nonnegative",
        ),
    )

    job_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("report_jobs.id"), primary_key=True)
    month: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(Uuid)
    owner_requests: Mapped[int] = mapped_column(Integer)
    owner_output_tokens: Mapped[int] = mapped_column(BigInteger)
    subscription_requests: Mapped[int] = mapped_column(Integer)
    subscription_output_tokens: Mapped[int] = mapped_column(BigInteger)
