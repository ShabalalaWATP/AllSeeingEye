"""Table definitions. Entities are mapped to and from these rows in the repositories."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from ase.adapters.persistence.base import Base, UTCDateTime
from ase.adapters.persistence.operational_models import (
    ActivitySampleRow,
    AlertRow,
    AoiRow,
    CollectionPlanRow,
    IndicatorRow,
    ReportRow,
    ReportVersionRow,
    ScheduleRow,
)

__all__ = [
    "AccountRequestRow",
    "ActivitySampleRow",
    "AdministrationLockRow",
    "AlertRow",
    "AoiRow",
    "AuditLogRow",
    "CollectionPlanRow",
    "IndicatorRow",
    "LlmProfileRow",
    "LlmUsageRow",
    "PasswordTokenRow",
    "RefreshTokenRow",
    "ReportRow",
    "ReportVersionRow",
    "ScheduleRow",
    "UserRow",
]


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(16))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    password_hash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    last_failed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    security_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class AdministrationLockRow(Base):
    """Singleton transaction lock for changes to global account administration."""

    __tablename__ = "administration_lock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class AccountRequestRow(Base):
    __tablename__ = "account_requests"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    decided_by: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class RefreshTokenRow(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    family_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    parent_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    issued_at: Mapped[datetime] = mapped_column(UTCDateTime)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)


class PasswordTokenRow(Base):
    __tablename__ = "password_tokens"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(16))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)


class AuditLogRow(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    subject: Mapped[str | None] = mapped_column(String(320), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class LlmProfileRow(Base):
    __tablename__ = "llm_profiles"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    base_url: Mapped[str] = mapped_column(String(512))
    model: Mapped[str] = mapped_column(String(120))
    api_key_encrypted: Mapped[str] = mapped_column(String(2048))
    api_key_hint: Mapped[str] = mapped_column(String(8))
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    max_output_tokens: Mapped[int] = mapped_column(Integer)
    temperature: Mapped[float] = mapped_column(Float)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime)
    reasoning_effort: Mapped[str | None] = mapped_column(String(16), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    tested_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    tested_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tested_config_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    test_generation: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class LlmUsageRow(Base):
    __tablename__ = "llm_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    profile_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    user_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    purpose: Mapped[str] = mapped_column(String(64))
    ok: Mapped[bool] = mapped_column(Boolean)
    latency_ms: Mapped[float] = mapped_column(Float)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
