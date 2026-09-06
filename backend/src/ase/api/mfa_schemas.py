"""Public challenge and personal MFA contracts, without stored secrets."""

import re
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from ase.domain.mfa import MfaMethod, PendingMfa


class MfaPendingOut(BaseModel):
    mfa_required: Literal[True] = True
    challenge_token: str = Field(repr=False)
    expires_at: datetime
    methods: list[MfaMethod]
    enrollment_required: bool
    email_sent: bool

    @classmethod
    def from_pending(cls, pending: PendingMfa) -> Self:
        return cls(
            challenge_token=pending.challenge_token,
            expires_at=pending.expires_at,
            methods=list(pending.methods),
            enrollment_required=pending.enrollment_required,
            email_sent=pending.email_sent,
        )


class MfaChallengeIn(BaseModel):
    challenge_token: str = Field(min_length=16, max_length=512, repr=False)


class MfaConfirmIn(MfaChallengeIn):
    code: str = Field(pattern=r"^[0-9]{6}$", repr=False)


class MfaVerifyIn(MfaChallengeIn):
    method: MfaMethod
    code: str = Field(min_length=6, max_length=40, repr=False)

    @model_validator(mode="after")
    def validate_code(self) -> Self:
        pattern = r"[0-9A-Fa-f]{32}" if self.method is MfaMethod.RECOVERY else r"[0-9]{6}"
        code = self.code.replace("-", "") if self.method is MfaMethod.RECOVERY else self.code
        if re.fullmatch(pattern, code) is None:
            raise ValueError("Enter a valid verification code.")
        self.code = code.upper()
        return self


class MfaPasswordIn(BaseModel):
    password: str = Field(min_length=1, max_length=128, repr=False)


class MfaStatusOut(BaseModel):
    methods: list[MfaMethod]
    available_methods: list[MfaMethod]
    required: bool
