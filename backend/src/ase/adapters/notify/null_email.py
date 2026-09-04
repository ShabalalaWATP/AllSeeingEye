"""No email transport is configured in Phase 0, so links are handed to the administrator instead."""

from __future__ import annotations

import structlog

from ase.domain.tokens import TokenPurpose

log = structlog.get_logger(__name__)


class NullEmailSender:
    async def send_link(self, to_email: str, purpose: TokenPurpose, link: str) -> bool:
        log.info("email_not_configured", purpose=purpose.value, recipient_domain=_domain(to_email))
        return False


def _domain(email: str) -> str:
    return email.rsplit("@", 1)[-1] if "@" in email else "unknown"
