"""Notification controls remain off until explicitly enabled by the account."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ase.domain.notification_delivery import EditionEmailPolicy


class FeedEnableIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    include_titles: bool = False


class FeedStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    enabled: bool
    include_titles: bool
    created_at: datetime | None


class FeedTokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    token: str
    feed_url: str
    username: str


class EmailPreferencesIn(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    enabled: bool = False
    include_names: bool = False


class EmailPreferencesOut(EmailPreferencesIn):
    available: bool
    confirmed: bool
    destination: str


class SubscriptionEmailIn(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    policy: EditionEmailPolicy = EditionEmailPolicy.NONE
    attention: bool = False
