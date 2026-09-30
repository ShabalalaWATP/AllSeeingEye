"""SMTP acceptance is not final inbox delivery; ambiguous sends are never retried."""

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from typing import Literal

from ase.domain.notification_delivery import DeliveryOutcome, NotificationEmail


class NullNotificationEmailSender:
    @property
    def available(self) -> bool:
        return False

    async def send(self, message: NotificationEmail) -> DeliveryOutcome:
        return DeliveryOutcome.UNAVAILABLE


class SmtpNotificationEmailSender:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        security: Literal["starttls", "tls"],
        from_email: str,
        username: str | None,
        password: str | None,
        timeout: int,
    ) -> None:
        self._host, self._port, self._security = host, port, security
        self._from, self._username, self._password = from_email, username, password
        self._timeout = timeout

    @property
    def available(self) -> bool:
        return True

    async def send(self, message: NotificationEmail) -> DeliveryOutcome:
        return await asyncio.to_thread(self._deliver, message)

    def _deliver(self, notice: NotificationEmail) -> DeliveryOutcome:
        attempted = False
        connection: smtplib.SMTP | None = None
        try:
            message = EmailMessage()
            message["From"], message["To"] = self._from, notice.recipient
            message["Subject"] = notice.subject
            message.set_content(notice.body)
            context = ssl.create_default_context()
            if self._security == "tls":
                connection = smtplib.SMTP_SSL(
                    self._host,
                    self._port,
                    timeout=self._timeout,
                    context=context,
                )
            else:
                connection = smtplib.SMTP(self._host, self._port, timeout=self._timeout)
                connection.ehlo()
                connection.starttls(context=context)
                connection.ehlo()
            if self._username and self._password:
                connection.login(self._username, self._password)
            attempted = True
            refused = connection.send_message(message)
            return DeliveryOutcome.RETRYABLE if refused else DeliveryOutcome.SENT
        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused, smtplib.SMTPDataError):
            return DeliveryOutcome.RETRYABLE
        except (OSError, smtplib.SMTPException, ValueError):
            # Never log SMTP exceptions: they may contain addresses, headers or secrets.
            return DeliveryOutcome.UNCERTAIN if attempted else DeliveryOutcome.RETRYABLE
        finally:
            if connection is not None:
                # QUIT failure after confirmed acceptance cannot turn success into failure.
                connection.close()
