"""Bounded, content-free records. Permissions and completed mutations stay distinct."""

from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from ase.domain.private_removal import RemovalScope, ReviewDecision, ReviewPurpose

MAX_EVENTS = 1000
MAX_PLAINTEXT = 2 * 1024 * 1024
MAX_CIPHERTEXT = 3 * 1024 * 1024
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Removal(Record):
    kind: Literal["removal"] = "removal"
    owner: UUID
    scope: RemovalScope
    target: UUID | None = None

    @model_validator(mode="after")
    def valid_scope(self) -> Self:
        if (self.scope is RemovalScope.ACCOUNT) != (self.target is None):
            raise ValueError("Invalid removal scope")
        return self


class Review(Record):
    kind: Literal["review"] = "review"
    owner: UUID
    decision: ReviewDecision
    purpose: ReviewPurpose
    revision: int = Field(ge=1)
    due: AwareDatetime


class Restriction(Record):
    """Operator-recorded instruction, never proof that its effect was applied."""

    kind: Literal["restriction"] = "restriction"
    owner: UUID
    restriction: Literal[
        "deactivate",
        "objection",
        "email_opt_out",
        "digest_opt_out",
        "subscription_opt_out",
        "push_revoke",
        "feed_revoke",
    ]
    target: UUID | None = None
    purpose: ReviewPurpose
    due: AwareDatetime

    @model_validator(mode="after")
    def valid_target(self) -> Self:
        if (self.restriction == "subscription_opt_out") != (self.target is not None):
            raise ValueError("Only subscription restrictions require a target")
        return self


class CopyReview(Record):
    """A selected operator policy for an opaque copy inventory reference."""

    kind: Literal["copy_review"] = "copy_review"
    reference: UUID
    category: Literal["scheduled", "manual", "offsite", "release", "mailbox", "export", "snapshot"]
    purpose: ReviewPurpose
    due: AwareDatetime
    max_age_days: int | None = Field(default=None, ge=1, le=36500)
    keep_count: int | None = Field(default=None, ge=1, le=10000)
    hold: bool = False

    @model_validator(mode="after")
    def explicit_policy(self) -> Self:
        if self.max_age_days is None and self.keep_count is None and not self.hold:
            raise ValueError("Record an actual selected period/count or an explicit hold")
        if self.category == "scheduled" and self.keep_count is not None and self.keep_count < 3:
            raise ValueError("Scheduled backup minimum is three")
        if self.category == "release" and self.keep_count is not None and self.keep_count < 2:
            raise ValueError("Release minimum is two")
        return self


Action = Annotated[Removal | Review | Restriction | CopyReview, Field(discriminator="kind")]


class Resolution(Record):
    operator: UUID
    at: AwareDatetime
    evidence_sha256: Digest


class Entry(Record):
    id: UUID
    sequence: int = Field(ge=1)
    actor: UUID
    at: AwareDatetime
    action: Action
    status: Literal["pending", "committed", "recorded", "not_applied"]
    resolution: Resolution | None = None

    @model_validator(mode="after")
    def consistent(self) -> Self:
        manual = isinstance(self.action, Restriction | CopyReview)
        if manual != (self.status == "recorded"):
            raise ValueError("Manual records are not committed database mutations")
        if self.status == "not_applied" and self.resolution is None:
            raise ValueError("Unapplied intent needs an evidenced resolution")
        if self.status == "pending" and self.resolution is not None:
            raise ValueError("Pending intent cannot be resolved")
        if isinstance(self.action, Review | Restriction | CopyReview) and not (
            0 < (self.action.due - self.at).total_seconds() <= 90 * 86400
        ):
            raise ValueError("Next review must be within ninety days")
        return self


class JournalDocument(Record):
    format: Literal[1] = 1
    journal_id: UUID
    created_at: AwareDatetime
    entries: list[Entry] = Field(max_length=MAX_EVENTS)

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if [event.sequence for event in self.entries] != list(range(1, len(self.entries) + 1)):
            raise ValueError("Journal sequence is incomplete")
        if len({event.id for event in self.entries}) != len(self.entries):
            raise ValueError("Duplicate journal event")
        if sum(event.status == "pending" for event in self.entries) > 1:
            raise ValueError("Multiple uncertain mutations")
        return self


def inspection(document: JournalDocument, head: str, now: datetime) -> dict[str, object]:
    """Evidence for manual reconciliation, never an authorisation to reactivate."""
    return {
        "journal_id": str(document.journal_id),
        "head_sha256": head,
        "activation_authorised": False,
        "coverage": "Only these recorded actions; investigate earlier and unrecorded decisions.",
        "unresolved_intents": [str(e.id) for e in document.entries if e.status == "pending"],
        "overdue_record_ids": [
            str(e.id)
            for e in document.entries
            if isinstance(e.action, Review | Restriction | CopyReview)
            and e.action.due <= now
            and e.status in {"committed", "recorded"}
        ],
        "events": [e.model_dump(mode="json") for e in document.entries],
        "required_checks": [
            "Obtain the latest trusted journal; an older authentic copy can omit decisions.",
            "Keep all restored services and outbound delivery offline.",
            "Apply current restrictions/holds before any removal; review-only is not deletion.",
            "Verify installation, restored target, operator authority and unrecorded decisions.",
            "Reconcile each entry and record evidence outside the affected backups.",
            "Obtain separate operator approval before activation; this report grants none.",
        ],
    }
