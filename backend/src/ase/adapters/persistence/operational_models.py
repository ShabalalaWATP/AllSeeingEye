"""Durable intelligence records, configuration and bounded operational aggregates."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime


class ReportRow(Base):
    __tablename__ = "reports"

    team_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("teams.id", name="fk_reports_team_id_teams"), nullable=True, index=True
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    template: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(200))
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    period_from: Mapped[datetime] = mapped_column(UTCDateTime)
    period_to: Mapped[datetime] = mapped_column(UTCDateTime)
    data_cutoff: Mapped[datetime] = mapped_column(UTCDateTime)
    status: Mapped[str] = mapped_column(String(16), index=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    latest_version: Mapped[int] = mapped_column(Integer, default=1)


class AoiRow(Base):
    __tablename__ = "aois"

    team_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("teams.id", name="fk_aois_team_id_teams"), nullable=True, index=True
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(1000), default="")
    kind: Mapped[str] = mapped_column(String(16))
    west: Mapped[float | None] = mapped_column(Float, nullable=True)
    south: Mapped[float | None] = mapped_column(Float, nullable=True)
    east: Mapped[float | None] = mapped_column(Float, nullable=True)
    north: Mapped[float | None] = mapped_column(Float, nullable=True)
    countries: Mapped[list[Any]] = mapped_column(JSON, default=list)
    created_by: Mapped[UUID] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class CollectionPlanRow(Base):
    __tablename__ = "collection_plans"

    team_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("teams.id", name="fk_collection_plans_team_id_teams"),
        nullable=True,
        index=True,
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(2000), default="")
    aoi_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    countries: Mapped[list[Any]] = mapped_column(JSON, default=list)
    pirs: Mapped[list[Any]] = mapped_column(JSON, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class ActivitySampleRow(Base):
    __tablename__ = "activity_samples"
    __table_args__ = (
        UniqueConstraint("kind", "key", "hour", name="uq_activity_samples_kind_key_hour"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(40))
    key: Mapped[str] = mapped_column(String(64))
    hour: Mapped[datetime] = mapped_column(UTCDateTime)
    value: Mapped[int] = mapped_column(Integer)


class ReportVersionRow(Base):
    __tablename__ = "report_versions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    report_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("reports.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    body: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    findings: Mapped[list[Any]] = mapped_column(JSON, default=list)
    evidence: Mapped[list[Any]] = mapped_column(JSON, default=list)
    quality: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    markdown: Mapped[str] = mapped_column(Text)
    profile_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    model: Mapped[str] = mapped_column(String(120))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float)
    attempts: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class IndicatorRow(Base):
    __tablename__ = "indicators"

    team_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("teams.id", name="fk_indicators_team_id_teams"), nullable=True, index=True
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(1000), default="")
    plan_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    countries: Mapped[list[Any]] = mapped_column(JSON, default=list)
    west: Mapped[float | None] = mapped_column(Float, nullable=True)
    south: Mapped[float | None] = mapped_column(Float, nullable=True)
    east: Mapped[float | None] = mapped_column(Float, nullable=True)
    north: Mapped[float | None] = mapped_column(Float, nullable=True)
    categories: Mapped[list[Any]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[Any]] = mapped_column(JSON, default=list)
    threshold: Mapped[int] = mapped_column(Integer, default=1)
    window_minutes: Mapped[int] = mapped_column(Integer, default=60)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=60)
    severity_floor: Mapped[float] = mapped_column(Float, default=0.0)
    report_template: Mapped[str | None] = mapped_column(String(40), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)


class AlertRow(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(
            "(indicator_id IS NOT NULL AND schedule_id IS NULL) OR "
            "(indicator_id IS NULL AND schedule_id IS NOT NULL)",
            name="ck_alerts_one_origin",
        ),
    )

    team_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("teams.id", name="fk_alerts_team_id_teams"), nullable=True, index=True
    )
    created_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    indicator_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    schedule_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    fired_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(String(1000), default="")
    count: Mapped[int] = mapped_column(Integer)
    threshold: Mapped[int] = mapped_column(Integer)
    event_ids: Mapped[list[Any]] = mapped_column(JSON, default=list)
    countries: Mapped[list[Any]] = mapped_column(JSON, default=list)
    acknowledged_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    acknowledged_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    report_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)


class ScheduleRow(Base):
    __tablename__ = "schedules"

    team_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("teams.id", name="fk_schedules_team_id_teams"), nullable=True, index=True
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    template_id: Mapped[str] = mapped_column(String(40))
    question: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    notify_on_change: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    last_change: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    research_options: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    country_iso: Mapped[str | None] = mapped_column(String(2), nullable=True)
    plan_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    hour_utc: Mapped[int] = mapped_column(Integer)
    cadence: Mapped[str] = mapped_column(String(16))
    weekday: Mapped[int] = mapped_column(Integer, default=0)
    window_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[UUID] = mapped_column(Uuid, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    next_run_at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_report_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(300), nullable=True)
