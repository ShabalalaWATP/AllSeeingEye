"""SMTP transport contracts without real mail or network connections."""

from __future__ import annotations

import smtplib
import ssl
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from ase.adapters.notify.null_email import NullEmailSender
from ase.container.email import build_email_sender
from ase.domain.tokens import TokenPurpose
from ase.infrastructure.settings import Environment, Settings


def configured(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "env": Environment.TEST,
        "smtp_host": "mail.example.com",
        "smtp_from_email": "accounts@example.com",
        "smtp_username": "test-sender",
        "smtp_password": SecretStr("test-mail-password"),
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


async def test_unconfigured_never_delivers_codes_or_links() -> None:
    sender = build_email_sender(Settings(_env_file=None, env=Environment.TEST))
    assert isinstance(sender, NullEmailSender)
    assert not sender.available
    assert not await sender.send_code("user@example.com", "123456")
    assert not await sender.send_link("user@example.com", TokenPurpose.RESET, "https://app.test")


async def test_starttls_precedes_credentials_and_code_delivery() -> None:
    sender = build_email_sender(configured())
    assert sender.available
    with patch("ase.adapters.notify.smtp_email.smtplib.SMTP") as factory:
        connection = factory.return_value
        connection.send_message.return_value = {}
        assert await sender.send_code("user@example.com", "123456")
    factory.assert_called_once_with("mail.example.com", 587, timeout=10)
    assert [call[0] for call in connection.method_calls] == [
        "ehlo",
        "starttls",
        "ehlo",
        "login",
        "send_message",
    ]
    context = connection.starttls.call_args.kwargs["context"]
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname
    message = connection.send_message.call_args.args[0]
    assert message["To"] == "user@example.com"
    assert message["From"] == "accounts@example.com"
    assert "123456" in message.get_content()
    assert message.get_content_type() == "text/plain"


@pytest.mark.parametrize("purpose", list(TokenPurpose))
async def test_implicit_tls_delivers_account_links(purpose: TokenPurpose) -> None:
    sender = build_email_sender(configured(smtp_security="tls", smtp_port=465))
    with patch("ase.adapters.notify.smtp_email.smtplib.SMTP_SSL") as factory:
        connection = factory.return_value
        connection.send_message.return_value = {}
        assert await sender.send_link("user@example.com", purpose, "https://app.test/secret")
    assert factory.call_args.args == ("mail.example.com", 465)
    assert factory.call_args.kwargs["context"].check_hostname
    connection.starttls.assert_not_called()
    assert "https://app.test/secret" in connection.send_message.call_args.args[0].get_content()


async def test_tls_relay_without_credentials_does_not_login() -> None:
    sender = build_email_sender(configured(smtp_username=None, smtp_password=None))
    with patch("ase.adapters.notify.smtp_email.smtplib.SMTP") as factory:
        factory.return_value.send_message.return_value = {}
        assert await sender.send_code("user@example.com", "123456")
    factory.return_value.login.assert_not_called()


@pytest.mark.parametrize("error", [OSError("private"), smtplib.SMTPException("private")])
async def test_delivery_failure_does_not_log_exception_or_code(error: Exception) -> None:
    sender = build_email_sender(configured())
    with (
        patch("ase.adapters.notify.smtp_email.smtplib.SMTP", side_effect=error),
        patch("ase.adapters.notify.smtp_email.log") as logger,
    ):
        assert not await sender.send_code("user@example.com", "123456")
    logger.warning.assert_called_once_with("account_email_delivery_failed")


async def test_missing_starttls_fails_without_password_or_message() -> None:
    sender = build_email_sender(configured())
    with patch("ase.adapters.notify.smtp_email.smtplib.SMTP") as factory:
        connection = factory.return_value
        connection.starttls.side_effect = smtplib.SMTPNotSupportedError("TLS unavailable")
        assert not await sender.send_code("user@example.com", "123456")
    connection.login.assert_not_called()
    connection.send_message.assert_not_called()


async def test_recipient_refusal_is_not_success() -> None:
    sender = build_email_sender(configured())
    with patch("ase.adapters.notify.smtp_email.smtplib.SMTP") as factory:
        factory.return_value.send_message.return_value = {"user@example.com": (550, b"Refused")}
        assert not await sender.send_code("user@example.com", "123456")


async def test_header_injection_fails_before_network() -> None:
    sender = build_email_sender(configured())
    with patch("ase.adapters.notify.smtp_email.smtplib.SMTP") as factory:
        assert not await sender.send_code("user@example.com\r\nBcc: other@example.com", "123456")
    factory.assert_not_called()


@pytest.mark.parametrize(
    "overrides",
    [
        {"smtp_host": None},
        {"smtp_from_email": None},
        {"smtp_from_email": "bad\r\naddress"},
        {"smtp_host": "bad host"},
        {"smtp_username": None},
        {"smtp_password": None},
        {"smtp_password": SecretStr("")},
        {"smtp_security": "none"},
        {"smtp_port": 0},
        {"smtp_timeout_seconds": 31},
        {"smtp_host": None, "smtp_from_email": None},
    ],
)
def test_invalid_smtp_configuration_fails_closed(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        configured(**overrides)


def test_smtp_password_is_redacted_in_settings_representation() -> None:
    assert "test-mail-password" not in repr(configured())
