"""Webhook read contracts intentionally have no URL or credential field."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class AlertRoutingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email_enabled: bool = False
    webhook_id: UUID | None = None
    expected_revision: int = Field(ge=0)


class AlertRoutingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    indicator_id: UUID
    configured_by: UUID
    email_enabled: bool
    webhook_id: UUID | None
    revision: int
    can_manage: bool


class AlertDestinationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    url: SecretStr = Field(min_length=1, max_length=2048)
    team_id: UUID | None = None


class AlertDestinationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    created_by: UUID
    team_id: UUID | None
    enabled: bool
    created_at: datetime


class AlertDestinationsOut(BaseModel):
    items: list[AlertDestinationOut]


class AlertRoutingCapabilitiesOut(BaseModel):
    installation_copy_enabled: bool
    in_app_required: bool = True
    installation_copy_notice: str = (
        "An administrator-controlled installation webhook receives a separate copy of all alerts, "
        "including personal and team alerts, with rule name, title, summary, "
        "countries and event IDs. "
        "Rule choices do not disable this copy."
    )
