"""Immutable subscription revisions and durable edition, attempt and delivery rows."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime

_ACTIVE = "workflow IN ('pending','queued','running','retry_wait','paused','blocked')"


class SubscriptionRevisionRow(Base):
    __tablename__ = "subscription_revisions"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_subscription_revisions_revision"),
        CheckConstraint("length(request_snapshot) <= 65536", name="ck_subscription_revision_size"),
    )

    subscription_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("schedules.id"), primary_key=True
    )
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    team_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("teams.id"), nullable=True)
    request_snapshot: Mapped[str] = mapped_column(Text)
    compatibility_fingerprint: Mapped[str] = mapped_column(String(64))
    recurrence_policy: Mapped[str] = mapped_column(String(32))
    collection_policy: Mapped[str] = mapped_column(String(32))
    enabled: Mapped[bool] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    brief_revision_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)


class SubscriptionEditionRow(Base):
    __tablename__ = "subscription_editions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["subscription_id", "frozen_revision"],
            ["subscription_revisions.subscription_id", "subscription_revisions.revision"],
            name="fk_subscription_edition_revision",
        ),
        UniqueConstraint("subscription_id", "due_at_utc", name="uq_subscription_edition_due"),
        UniqueConstraint(
            "subscription_id", "trigger", "request_uuid", name="uq_subscription_edition_manual"
        ),
        UniqueConstraint("job_id", name="uq_subscription_edition_job"),
        UniqueConstraint("version_id", name="uq_subscription_edition_version"),
        CheckConstraint(
            "(trigger IN ('scheduled','catch_up') AND due_at_utc IS NOT NULL AND "
            "request_uuid IS NULL) OR (trigger IN ('run_now','baseline') AND "
            "due_at_utc IS NULL AND request_uuid IS NOT NULL)",
            name="ck_subscription_edition_trigger",
        ),
        CheckConstraint(
            "workflow IN ('pending','queued','running','retry_wait','paused','blocked',"
            "'completed','failed','cancelled','skipped')",
            name="ck_subscription_edition_workflow",
        ),
        CheckConstraint(
            "report_quality IN ('absent','ready','needs_review','failed')",
            name="ck_subscription_edition_quality",
        ),
        CheckConstraint(
            "coverage IN ('complete_for_plan','partial','insufficient','unknown')",
            name="ck_subscription_edition_coverage",
        ),
        CheckConstraint("revision >= 1", name="ck_subscription_edition_revision"),
        CheckConstraint("requested_start < requested_end", name="ck_subscription_edition_window"),
        Index(
            "ix_subscription_edition_active",
            "subscription_id",
            unique=True,
            sqlite_where=text(_ACTIVE),
            postgresql_where=text(_ACTIVE),
        ),
        Index("ix_subscription_edition_due_status", "workflow", "due_at_utc", "id"),
        Index("ix_subscription_edition_history", "subscription_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    subscription_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("schedules.id"))
    trigger: Mapped[str] = mapped_column(String(16))
    due_at_utc: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    request_uuid: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    frozen_revision: Mapped[int] = mapped_column(Integer)
    requested_start: Mapped[datetime] = mapped_column(UTCDateTime)
    requested_end: Mapped[datetime] = mapped_column(UTCDateTime)
    effective_intervals: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    gaps: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    compatibility_fingerprint: Mapped[str] = mapped_column(String(64))
    baseline_version_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("report_versions.id"), nullable=True
    )
    workflow: Mapped[str] = mapped_column(String(20))
    report_quality: Mapped[str] = mapped_column(String(20))
    coverage: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revision: Mapped[int] = mapped_column(Integer)
    job_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("report_jobs.id"), nullable=True)
    report_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("reports.id"), nullable=True)
    version_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("report_versions.id"), nullable=True
    )
    safe_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    covered_by_edition_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    accepted_as_baseline: Mapped[bool] = mapped_column(default=False)


class SubscriptionEditionComparisonRow(Base):
    __tablename__ = "subscription_edition_comparisons"
    __table_args__ = (
        CheckConstraint(
            "state IN ('failure','insufficient_coverage',"
            "'significant_contradiction_or_correction','assessment_changed',"
            "'new_evidence_broadly_unchanged_assessment',"
            "'no_new_relevant_captured_evidence')",
            name="ck_subscription_comparison_state",
        ),
    )

    edition_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("subscription_editions.id"), primary_key=True
    )
    previous_version_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("report_versions.id"), nullable=True
    )
    current_version_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("report_versions.id"))
    state: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class SubscriptionLineageRow(Base):
    __tablename__ = "subscription_lineages"
    __table_args__ = (CheckConstraint("revision >= 1", name="ck_subscription_lineage_revision"),)

    subscription_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("schedules.id"), primary_key=True
    )
    compatibility_fingerprint: Mapped[str] = mapped_column(String(64))
    analytical_baseline_version_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("report_versions.id"), nullable=True
    )
    covered_intervals: Mapped[list[dict[str, str]]] = mapped_column(JSON)
    complete_cutoff: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revision: Mapped[int] = mapped_column(Integer)


class SubscriptionAttemptRow(Base):
    __tablename__ = "subscription_edition_attempts"
    __table_args__ = (
        UniqueConstraint("edition_id", "number", name="uq_subscription_attempt_number"),
        CheckConstraint("number >= 1", name="ck_subscription_attempt_number"),
        CheckConstraint(
            "reserved_requests >= 0 AND actual_requests >= 0 AND "
            "reserved_output_tokens >= 0 AND actual_output_tokens >= 0",
            name="ck_subscription_attempt_usage",
        ),
        Index("ix_subscription_attempt_history", "edition_id", "number"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    edition_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("subscription_editions.id"))
    job_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("report_jobs.id"), nullable=True)
    number: Mapped[int] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(120))
    started_at: Mapped[datetime] = mapped_column(UTCDateTime)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    outcome: Mapped[str] = mapped_column(String(120))
    next_retry_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    lease_token: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    job_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reserved_requests: Mapped[int] = mapped_column(Integer)
    actual_requests: Mapped[int] = mapped_column(Integer)
    reserved_output_tokens: Mapped[int] = mapped_column(Integer)
    actual_output_tokens: Mapped[int] = mapped_column(Integer)


class SubscriptionDeliveryRow(Base):
    __tablename__ = "subscription_delivery_outbox"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_subscription_delivery_key"),
        CheckConstraint("attempts BETWEEN 0 AND 100", name="ck_subscription_delivery_attempts"),
        Index("ix_subscription_delivery_state", "state", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    edition_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("subscription_editions.id"))
    channel: Mapped[str] = mapped_column(String(40))
    destination_ref: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    event_kind: Mapped[str] = mapped_column(String(80))
    idempotency_key: Mapped[UUID] = mapped_column(Uuid)
    state: Mapped[str] = mapped_column(String(20))
    attempts: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
