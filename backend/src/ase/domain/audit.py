"""Append-only audit trail entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class AuditAction(StrEnum):
    LOGIN_SUCCEEDED = "login_succeeded"
    LOGIN_FAILED = "login_failed"
    TOTP_ENROLMENT_STARTED = "totp_enrolment_started"
    TOTP_ENABLED = "totp_enabled"
    TOTP_DISABLED = "totp_disabled"
    TOTP_RECOVERED = "totp_recovered"
    TOTP_FAILED = "totp_failed"
    ACCOUNT_LOCKED = "account_locked"
    TOKEN_REFRESHED = "token_refreshed"
    REFRESH_REUSE_DETECTED = "refresh_reuse_detected"
    LOGOUT = "logout"
    ACCOUNT_REQUESTED = "account_requested"
    ACCOUNT_REQUEST_APPROVED = "account_request_approved"
    ACCOUNT_REQUEST_REJECTED = "account_request_rejected"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_SET = "password_set"
    USER_UPDATED = "user_updated"
    RESET_LINK_ISSUED = "reset_link_issued"
    LLM_PROFILE_CREATED = "llm_profile_created"
    LLM_PROFILE_UPDATED = "llm_profile_updated"
    LLM_PROFILE_DELETED = "llm_profile_deleted"
    LLM_PROFILE_TESTED = "llm_profile_tested"
    REPORT_GENERATED = "report_generated"
    REPORT_DELETED = "report_deleted"
    AOI_CREATED = "aoi_created"
    AOI_DELETED = "aoi_deleted"
    PLAN_CREATED = "plan_created"
    PLAN_UPDATED = "plan_updated"
    PLAN_DELETED = "plan_deleted"
    INDICATOR_CREATED = "indicator_created"
    INDICATOR_UPDATED = "indicator_updated"
    INDICATOR_DELETED = "indicator_deleted"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    SCHEDULE_CREATED = "schedule_created"
    SCHEDULE_UPDATED = "schedule_updated"
    SCHEDULE_DELETED = "schedule_deleted"


@dataclass(slots=True)
class AuditEntry:
    at: datetime
    action: AuditAction
    actor_user_id: UUID | None = None
    subject: str | None = None
    ip: str | None = None
    details: dict[str, object] = field(default_factory=dict)
    id: int | None = None
