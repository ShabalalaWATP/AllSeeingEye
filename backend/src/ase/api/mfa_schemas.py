"""Public challenge and personal MFA contracts, without stored secrets."""

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field

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


class MfaVerifyIn(MfaConfirmIn):
    method: MfaMethod


class MfaPasswordIn(BaseModel):
    password: str = Field(min_length=1, max_length=128, repr=False)


class MfaStatusOut(BaseModel):
    methods: list[MfaMethod]
    available_methods: list[MfaMethod]
    required: bool
