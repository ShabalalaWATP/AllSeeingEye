"""Recovery codes are returned once, only after fresh factor verification."""

from typing import Literal

from pydantic import BaseModel, Field

from ase.api.mfa_schemas import MfaPasswordIn


class RecoveryStatusOut(BaseModel):
    remaining: int
    available: bool


class RecoveryGenerateIn(MfaPasswordIn):
    method: Literal["authenticator", "email"]
    code: str = Field(pattern=r"^[0-9]{6}$", repr=False)
    challenge_token: str | None = Field(default=None, min_length=16, max_length=512, repr=False)


class RecoveryCodesOut(BaseModel):
    codes: list[str] = Field(repr=False)
