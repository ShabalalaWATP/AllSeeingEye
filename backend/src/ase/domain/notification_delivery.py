"""Delivery intents describe outcomes without promising exactly-once network delivery."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class DeliveryOutcome(StrEnum):
    SENT = "sent"
    RETRYABLE = "retryable"
    UNCERTAIN = "uncertain"
    UNAVAILABLE = "unavailable"


class EditionEmailPolicy(StrEnum):
    NONE = "none"
    MATERIAL = "material_changes"
    EVERY = "every_edition"


@dataclass(frozen=True, slots=True)
class EmailPreferences:
    enabled: bool = False
    include_names: bool = False


@dataclass(frozen=True, slots=True)
class SubscriptionEmailPreferences:
    policy: EditionEmailPolicy = EditionEmailPolicy.NONE
    attention: bool = False


@dataclass(frozen=True, slots=True)
class ClaimedDelivery:
    id: UUID
    resource_id: UUID
    recipient_id: UUID
    event_kind: str
    lease_token: UUID
    attempts: int


@dataclass(frozen=True, slots=True)
class NotificationEmail:
    recipient: str
    subject: str
    body: str


@dataclass(frozen=True, slots=True)
class DeliveryStatus:
    id: UUID
    event_kind: str
    state: str
    safe_reason: str | None
    updated_at: datetime
