"""The connector fixture retains configured and unavailable default email transports."""

import pytest

from ase.adapters.notify.null_email import NullEmailSender
from ase.adapters.notify.smtp_email import SmtpEmailSender
from event_app_fixtures import email_sender as _email_sender  # noqa: F401
from event_app_fixtures import feed_connectors as _feed_connectors  # noqa: F401


@pytest.fixture(params=[False, True], ids=["unconfigured", "configured"])
def settings(request, settings):
    return settings.model_copy(
        update={
            "smtp_host": "relay.example.test" if request.param else None,
            "smtp_from_email": "sender@example.test" if request.param else None,
        }
    )


def test_event_fixture_uses_the_default_transport_from_settings(container, settings, email_sender):
    assert email_sender is None
    expected = SmtpEmailSender if settings.smtp_host else NullEmailSender
    assert type(container.email_sender) is expected
    assert container.email_sender.available is bool(settings.smtp_host)
