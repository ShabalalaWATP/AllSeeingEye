"""Synthetic SMTP transport outcomes never leak contents or claim final delivery."""

import smtplib
from unittest.mock import Mock

import pytest

from ase.adapters.notify.notification_email import SmtpNotificationEmailSender
from ase.domain.notification_delivery import DeliveryOutcome, NotificationEmail


def sender():
    return SmtpNotificationEmailSender(
        host="relay.example.invalid",
        port=587,
        security="starttls",
        from_email="service@example.invalid",
        username=None,
        password=None,
        timeout=2,
    )


@pytest.mark.parametrize(
    "failure,expected",
    [
        (None, DeliveryOutcome.SENT),
        (TimeoutError("secret destination"), DeliveryOutcome.UNCERTAIN),
        (smtplib.SMTPServerDisconnected("secret recipient"), DeliveryOutcome.UNCERTAIN),
        (smtplib.SMTPDataError(450, b"secret recipient"), DeliveryOutcome.RETRYABLE),
        (smtplib.SMTPRecipientsRefused({"secret": (450, "refused")}), DeliveryOutcome.RETRYABLE),
    ],
)
async def test_data_phase_outcome(monkeypatch, caplog, failure, expected):
    connection = Mock()
    connection.send_message.return_value = {}
    connection.send_message.side_effect = failure
    monkeypatch.setattr(smtplib, "SMTP", Mock(return_value=connection))
    message = NotificationEmail("recipient@example.invalid", "Private subject", "Private body")
    assert await sender().send(message) is expected
    connection.starttls.assert_called_once()
    connection.close.assert_called_once()
    assert "secret" not in caplog.text and "Private" not in caplog.text


async def test_failure_before_data_is_safe_to_retry(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", Mock(side_effect=TimeoutError))
    assert (
        await sender().send(NotificationEmail("a@example.invalid", "Notice", "Link"))
        is DeliveryOutcome.RETRYABLE
    )
