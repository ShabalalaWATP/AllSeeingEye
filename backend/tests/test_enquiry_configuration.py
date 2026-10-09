"""Configuration and operator delivery never become a public arbitrary-mail facility."""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from ase.adapters.notify.null_email import NullEmailSender
from ase.container import Container
from ase.container.email import build_email_sender
from ase.domain.enterprise_enquiries import EnquiryDetails
from ase.infrastructure.settings import Settings
from test_enterprise_enquiries import PAYLOAD


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"enterprise_enquiry_notify_email": "operator@example.com"},
        {"smtp_host": "mail.example.com", "smtp_from_email": "sender@example.com"},
    ],
)
def test_enabled_requires_recipient_and_real_transport(values):
    with pytest.raises(ValidationError, match="Enterprise enquiries require"):
        Settings(_env_file=None, env="test", enterprise_enquiries_enabled=True, **values)


async def test_notice_recipient_and_subject_are_configuration_only():
    settings = Settings(
        _env_file=None,
        env="test",
        enterprise_enquiries_enabled=True,
        enterprise_enquiry_notify_email="operator@example.com",
        smtp_host="mail.example.com",
        smtp_from_email="sender@example.com",
    )
    sender = build_email_sender(settings)
    with patch("ase.adapters.notify.smtp_email.smtplib.SMTP") as factory:
        factory.return_value.send_message.return_value = {}
        assert await sender.send_operator_notice("Visitor\nBcc: attacker@example.com")
    message = factory.return_value.send_message.call_args.args[0]
    assert message["To"] == "operator@example.com"
    assert message["Subject"] == "The All Seeing Eye: deployment enquiry"
    assert message["Bcc"] is None
    assert message.get_content_type() == "text/plain"
    assert "attacker@example.com" in message.get_content()


async def test_notice_without_configured_recipient_never_sends():
    sender = build_email_sender(
        Settings(
            _env_file=None,
            env="test",
            smtp_host="mail.example.com",
            smtp_from_email="sender@example.com",
        )
    )
    with patch("ase.adapters.notify.smtp_email.smtplib.SMTP") as factory:
        assert not await sender.send_operator_notice("private content")
    factory.assert_not_called()
    assert not await NullEmailSender().send_operator_notice("private content")


def test_startup_refuses_an_unavailable_operator_transport():
    settings = Settings(
        _env_file=None,
        env="test",
        enterprise_enquiries_enabled=True,
        enterprise_enquiry_notify_email="operator@example.com",
        smtp_host="mail.example.com",
        smtp_from_email="sender@example.com",
    )
    with (
        patch("ase.container.build_email_sender", return_value=NullEmailSender()),
        pytest.raises(ValueError, match="configured email transport"),
    ):
        Container(settings, connectors=())


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "\n"),
        ("organisation", ""),
        ("email", "invalid"),
        ("expected_users", "none"),
        ("message", "x" * 2001),
    ],
)
def test_domain_rejects_invalid_values_outside_http(field, value):
    with pytest.raises(ValueError):
        EnquiryDetails(**{**PAYLOAD, field: value})
