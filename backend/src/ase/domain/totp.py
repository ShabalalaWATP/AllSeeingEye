"""Administrator second-factor state and one-time enrolment details."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TotpState:
    user_id: UUID
    secret_encrypted: str | None = field(repr=False)
    pending_encrypted: str | None = field(repr=False)
    pending_expires_at: datetime | None
    last_step: int | None

    @property
    def enabled(self) -> bool:
        return self.secret_encrypted is not None


@dataclass(frozen=True, slots=True)
class TotpEnrolment:
    secret: str = field(repr=False)
    provisioning_uri: str = field(repr=False)
    encrypted: str = field(repr=False)
