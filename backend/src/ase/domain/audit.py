"""Append-only audit trail entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class AuditAction(StrEnum):
    SOURCE_ACTIVATION_CHANGED = "source_activation_changed"
    FIRMS_DRAFT_SAVED = "firms.draft_saved"
    FIRMS_TEST_STARTED = "firms.test_started"
    FIRMS_TESTED = "firms.tested"
    FIRMS_CONFIRMED = "firms.confirmed"
    FIRMS_CLEARED = "firms.cleared"
    SOURCE_TESTED = "source_tested"
    SOURCE_RESET = "source_reset"
    SOURCE_RATING_REVIEWED = "source_rating_reviewed"
    SOURCE_ASSESSMENT_FROZEN = "source_assessment_frozen"
    LOGIN_SUCCEEDED = "login_succeeded"
    LOGIN_FAILED = "login_failed"
    TOTP_ENROLMENT_STARTED = "totp_enrolment_started"
    TOTP_ENABLED = "totp_enabled"
    TOTP_DISABLED = "totp_disabled"
    TOTP_RECOVERED = "totp_recovered"
    TOTP_FAILED = "totp_failed"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    MFA_RECOVERED = "mfa_recovered"
    MFA_RECOVERY_CODES_GENERATED = "mfa_recovery_codes_generated"
    ACCOUNT_LOCKED = "account_locked"
    TOKEN_REFRESHED = "token_refreshed"
    REFRESH_REUSE_DETECTED = "refresh_reuse_detected"
    LOGOUT = "logout"
    ACCOUNT_REQUESTED = "account_requested"
    ACCOUNT_REQUEST_APPROVED = "account_request_approved"
    ACCOUNT_REQUEST_REJECTED = "account_request_rejected"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_SET = "password_set"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_CHANGE_FAILED = "password_change_failed"
    USER_UPDATED = "user_updated"
    RESET_LINK_ISSUED = "reset_link_issued"
    LLM_PROFILE_CREATED = "llm_profile_created"
    LLM_PROFILE_UPDATED = "llm_profile_updated"
    LLM_PROFILE_DELETED = "llm_profile_deleted"
    LLM_PROFILE_TESTED = "llm_profile_tested"
    LLM_PROFILE_TEST_STARTED = "llm_profile_test_started"
    LLM_CONNECTION_ACTIVATED = "llm_connection_activated"
    LLM_CONNECTION_RESET = "llm_connection_reset"
    REPORT_GENERATED = "report_generated"
    REPORT_DELETED = "report_deleted"
    LIBRARY_UPDATED = "library_updated"
    LIBRARY_REMOVED = "library_removed"
    CLAIM_CREATED = "claim.created"
    CLAIM_REVISED = "claim.revised"
    IDENTITY_CREATED = "identity.created"
    IDENTITY_REVISED = "identity.revised"
    RELATIONSHIP_CREATED = "relationship.created"
    RELATIONSHIP_REVISED = "relationship.revised"
    MAP_VIEW_CREATED = "map_view_created"
    MAP_VIEW_REVISED = "map_view_revised"
    MAP_VIEW_ARCHIVED = "map_view_archived"
    AOI_CREATED = "aoi_created"
    AOI_DELETED = "aoi_deleted"
    PLAN_CREATED = "plan_created"
    PLAN_UPDATED = "plan_updated"
    PLAN_DELETED = "plan_deleted"
    INDICATOR_CREATED = "indicator_created"
    INDICATOR_UPDATED = "indicator_updated"
    INDICATOR_DELETED = "indicator_deleted"
    FORECAST_LEDGER_UPDATED = "forecast_ledger_updated"
    INDICATOR_LEDGER_UPDATED = "indicator_ledger_updated"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    SCHEDULE_CREATED = "schedule_created"
    SCHEDULE_UPDATED = "schedule_updated"
    SCHEDULE_DELETED = "schedule_deleted"
    LEGACY_SCOPE_CONFLICT = "legacy_scope_conflict"
    TEAM_CREATED = "team_created"
    TEAM_UPDATED = "team_updated"
    TEAM_MEMBER_SET = "team_member_set"
    TEAM_MEMBER_REMOVED = "team_member_removed"


@dataclass(slots=True)
class AuditEntry:
    at: datetime
    action: AuditAction
    actor_user_id: UUID | None = None
    subject: str | None = None
    ip: str | None = None
    details: dict[str, object] = field(default_factory=dict)
    id: int | None = None
