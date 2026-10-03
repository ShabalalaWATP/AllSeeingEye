"""Fake connector inventory with the application's normal email composition."""

import pytest

from feeds_helpers import FakeConnector, make_spec


@pytest.fixture(name="feed_connectors")
def feed_connectors() -> list[FakeConnector]:
    """Give each source-control test a fresh connector and poll counter."""
    return [FakeConnector(make_spec("fake_feed"))]


@pytest.fixture(name="email_sender")
def email_sender() -> None:
    """Preserve the former custom app's default transport, rather than a recorder."""
    return None
