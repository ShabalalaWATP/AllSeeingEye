"""Private account mail delivered over certificate-verified SMTP TLS."""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from typing import Literal

import structlog

from ase.domain.tokens import TokenPurpose

log = structlog.get_logger(__name__)


class SmtpEmailSender:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        security: Literal["starttls", "tls"],
        from_email: str,
        username: str | None,
        password: str | None,
        timeout_seconds: int,
    ) -> None:
        self._host = host
        self._port = port
        self._security = security
        self._from_email = from_email
        self._username = username
        self._password = password
        self._timeout = timeout_seconds

    @property
    def available(self) -> bool:
        return True

    async def send_code(self, to_email: str, code: str) -> bool:
        return await self._send(
            to_email,
            "Your All Seeing Eye verification code",
            f"Your verification code is: {code}\n\n"
            "This code expires shortly and can only be used once. "
            "Do not share it with anyone.\n\n"
            "If you did not request this code, do not use it.",
        )

    async def send_link(self, to_email: str, purpose: TokenPurpose, link: str) -> bool:
        action = (
            "Activate your account" if purpose is TokenPurpose.ACTIVATION else "Reset your password"
        )
        return await self._send(
            to_email,
            f"The All Seeing Eye: {action.lower()}",
            f"{action} by opening this link:\n\n{link}\n\n"
            "This link expires and can only be used once. "
            "If you did not request it, you can ignore this message.",
        )

    async def _send(self, to_email: str, subject: str, body: str) -> bool:
        try:
            message = EmailMessage()
            message["From"] = self._from_email
            message["To"] = to_email
            message["Subject"] = subject
            message.set_content(body)
            return await asyncio.to_thread(self._deliver, message)
        except (OSError, smtplib.SMTPException, ValueError):
            # Server exception text may echo message data, credentials or recipients.
            log.warning("account_email_delivery_failed")
            return False

    def _deliver(self, message: EmailMessage) -> bool:
        context = ssl.create_default_context()
        if self._security == "tls":
            connection: smtplib.SMTP = smtplib.SMTP_SSL(
                self._host, self._port, timeout=self._timeout, context=context
            )
        else:
            connection = smtplib.SMTP(self._host, self._port, timeout=self._timeout)
        with connection:
            if self._security == "starttls":
                connection.ehlo()
                connection.starttls(context=context)
                connection.ehlo()
            if self._username and self._password:
                connection.login(self._username, self._password)
            refused = connection.send_message(message)
            return not refused
