"""Strict self-service account credentials, excluded from model representations."""

from pydantic import BaseModel, ConfigDict, Field


class ChangePasswordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=128, repr=False)
    new_password: str = Field(min_length=1, max_length=128, repr=False)
    totp_code: str | None = Field(default=None, pattern=r"^[0-9]{6}$", repr=False)
    mfa_challenge_token: str | None = Field(default=None, min_length=16, max_length=512, repr=False)
    mfa_code: str | None = Field(default=None, pattern=r"^[0-9]{6}$", repr=False)
