"""Browser push carries one opaque identifier, never private alert content."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PushSubscription:
    endpoint: str = field(repr=False)
    p256dh: str = field(repr=False)
    auth: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class PushDevice:
    id: UUID
    endpoint_hash: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PushDelivery:
    id: UUID
    device_id: UUID
    alert_id: UUID
    lease_token: UUID
    subscription: PushSubscription


class PushOutcome(StrEnum):
    SENT = "sent"
    EXPIRED = "expired"
    REFUSED = "refused"
    UNCERTAIN = "uncertain"
