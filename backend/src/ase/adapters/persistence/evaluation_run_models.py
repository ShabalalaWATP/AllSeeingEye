"""Administrator evaluation runs: small summaries plus one bounded artefact each.

``active_slot`` is 1 while a run is running and NULL afterwards. Its unique
constraint is the database guarantee that only one run is active at a time; NULLs
never collide on SQLite or PostgreSQL.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, deferred, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime

# Shared with migration 0076 so the model and the schema cannot drift apart.
EVALUATION_RUN_CHECKS = (
    ("status IN ('running', 'completed', 'cancelled', 'stopped')", "ck_evaluation_runs_status"),
    (
        "(status = 'running' AND active_slot = 1) OR (status <> 'running' AND active_slot IS NULL)",
        "ck_evaluation_runs_active_slot",
    ),
    ("max_calls BETWEEN 1 AND 200", "ck_evaluation_runs_max_calls"),
    ("calls_reserved BETWEEN 0 AND max_calls", "ck_evaluation_runs_calls_reserved"),
    ("calls_failed BETWEEN 0 AND calls_reserved", "ck_evaluation_runs_calls_failed"),
)


class EvaluationRunRow(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        UniqueConstraint("active_slot", name="uq_evaluation_runs_active_slot"),
        *(CheckConstraint(sql, name=name) for sql, name in EVALUATION_RUN_CHECKS),
        Index("ix_evaluation_runs_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    actor_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # No foreign key: a deleted connection must not erase the record of its runs.
    profile_id: Mapped[UUID] = mapped_column(Uuid)
    profile_name: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(2048))
    profile_fingerprint: Mapped[str] = mapped_column(String(64))
    case_ids: Mapped[list[str]] = mapped_column(JSON)
    case_fingerprints: Mapped[dict[str, str]] = mapped_column(JSON)
    max_calls: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    stop_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    active_slot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    calls_reserved: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    calls_failed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    results: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    artefact: Mapped[bytes | None] = deferred(mapped_column(LargeBinary, nullable=True))
    has_artefact: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
