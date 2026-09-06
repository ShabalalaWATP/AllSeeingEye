"""Unavailable email transport. MFA codes never use the administrator link fallback."""

from __future__ import annotations

import structlog

from ase.domain.tokens import TokenPurpose

log = structlog.get_logger(__name__)


class NullEmailSender:
    @property
    def available(self) -> bool:
        return False

    async def send_code(self, to_email: str, code: str) -> bool:
        return False

    async def send_link(self, to_email: str, purpose: TokenPurpose, link: str) -> bool:
        log.info("email_not_configured", purpose=purpose.value, recipient_domain=_domain(to_email))
        return False


def _domain(email: str) -> str:
    return email.rsplit("@", 1)[-1] if "@" in email else "unknown"
