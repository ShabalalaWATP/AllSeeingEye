"""One global FIRMS credential with an expiring candidate and exact test proof."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class FirmsCredential:
    revision: int = 0
    active_revision: int = 0
    active_encrypted: str | None = field(default=None, repr=False)
    draft_encrypted: str | None = field(default=None, repr=False)
    draft_expires_at: datetime | None = None
    draft_area: str | None = None
    test_generation: int = 0
    tested_at: datetime | None = None
    tested_revision: int | None = None
    tested_actor: UUID | None = None
    tested_family: UUID | None = field(default=None, repr=False)
    tested_security_version: int | None = None

    def draft_valid(self, now: datetime, area: str) -> bool:
        return bool(
            self.draft_encrypted
            and self.draft_expires_at
            and self.draft_expires_at > now
            and self.draft_area == area
        )
