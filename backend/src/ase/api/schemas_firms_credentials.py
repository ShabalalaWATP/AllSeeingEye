"""Masked FIRMS connection metadata and bounded credential commands."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class FirmsRevisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)


class FirmsDraftIn(FirmsRevisionIn):
    api_key: SecretStr = Field(min_length=16, max_length=128)


class FirmsConfirmIn(FirmsRevisionIn):
    test_generation: int = Field(ge=1)


class FirmsConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    revision: int
    active_revision: int
    configured: bool
    credential_origin: Literal["environment", "database", "none"]
    environment_disabled: bool
    encryption_available: bool
    area: str
    draft_present: bool
    draft_expires_at: datetime | None
    tested_at: datetime | None
    test_generation: int
    test_ok: bool


class FirmsConnectionTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: FirmsConnectionOut
    ok: bool
    fetched: int
    message: str
