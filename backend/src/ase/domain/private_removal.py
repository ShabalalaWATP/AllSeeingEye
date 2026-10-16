"""Explicit operator decisions and precise, content-free private-removal previews."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class RemovalScope(StrEnum):
    ACCOUNT = "account"
    REPORT = "report"
    SUBSCRIPTION = "subscription"
    BRIEF = "brief"
    JOB = "job"


class ReviewDecision(StrEnum):
    RETAIN = "retain"
    HOLD = "hold"
    REMOVE = "remove"


class ReviewPurpose(StrEnum):
    QUARTERLY = "quarterly"
    ACCOUNT_CLOSURE = "account_closure"
    RIGHTS_REQUEST = "rights_request"
    PURPOSE_COMPLETE = "purpose_complete"


@dataclass(frozen=True)
class RemovalRequest:
    owner_id: UUID
    scope: RemovalScope
    target_id: UUID | None = None

    def __post_init__(self) -> None:
        if (self.scope is RemovalScope.ACCOUNT) != (self.target_id is None):
            raise ValueError("Account scope has no target; saved-work scope requires a target ID.")


@dataclass(frozen=True)
class NecessityReview:
    owner_id: UUID
    revision: int
    decision: ReviewDecision
    purpose: ReviewPurpose
    reviewed_at: datetime
    next_review_at: datetime
    erased_at: datetime | None = None


@dataclass(frozen=True)
class RemovalPlan:
    request: RemovalRequest
    counts: dict[str, int]
    blockers: tuple[str, ...]
    retained: tuple[str, ...]
    fingerprint: str
    necessity_review: NecessityReview | None = None


RETAINED_CATEGORIES = (
    "Shared team work, authorship, recipient copies and their independent retention requirements.",
    "Audit events, necessity decisions and minimal identity references for retained records.",
    "AI usage/reservations and allowance totals needed for accounting and uncertain calls.",
    "Backups, external archives, provider/mailbox/browser copies and previous exports.",
    "Other processes' in-memory private inputs until their normal expiry or process shutdown.",
)
