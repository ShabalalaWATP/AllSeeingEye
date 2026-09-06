"""Compose optional SMTP account mail without a code-delivery fallback."""

from ase.adapters.notify.null_email import NullEmailSender
from ase.adapters.notify.smtp_email import SmtpEmailSender
from ase.application.ports.services import EmailSender
from ase.infrastructure.settings import Settings


def build_email_sender(settings: Settings) -> EmailSender:
    if not settings.smtp_host or not settings.smtp_from_email:
        return NullEmailSender()
    return SmtpEmailSender(
        host=settings.smtp_host,
        port=settings.smtp_port,
        security=settings.smtp_security,
        from_email=str(settings.smtp_from_email),
        username=settings.smtp_username,
        password=settings.smtp_password.get_secret_value() if settings.smtp_password else None,
        timeout_seconds=settings.smtp_timeout_seconds,
    )
