"""Explicit external alert routes; stored in-app alerts are always retained."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from ase.domain.notification_delivery import NotificationEmail
from ase.domain.warning import Alert, Indicator

AlertChannel = Literal["email", "webhook", "installation_webhook"]


@dataclass(frozen=True, slots=True)
class AlertRoute:
    indicator_id: UUID
    configured_by: UUID
    email_enabled: bool = False
    webhook_id: UUID | None = None
    revision: int = 0


@dataclass(frozen=True, slots=True)
class AlertWebhookDestination:
    id: UUID
    name: str
    created_by: UUID
    team_id: UUID | None
    enabled: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AlertDeliveryClaim:
    id: UUID
    alert_id: UUID
    channel: AlertChannel
    destination_ref: str
    lease_token: UUID
    attempts: int


@dataclass(frozen=True, slots=True)
class PreparedAlertDelivery:
    alert: Alert
    indicator: Indicator
    email: NotificationEmail | None = None
    webhook_url: str | None = field(default=None, repr=False)
