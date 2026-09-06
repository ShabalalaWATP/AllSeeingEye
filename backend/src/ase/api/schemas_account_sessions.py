"""Safe session metadata for the signed-in account."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AccountSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    current: bool
    created_at: datetime
    last_active_at: datetime
    expires_at: datetime
    user_agent: str | None
    ip: str | None


class AccountSessionsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[AccountSessionOut]
    truncated: bool
