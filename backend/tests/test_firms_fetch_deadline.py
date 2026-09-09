"""Fixed FIRMS world-collection deadlines leave other feeds and explicit limits intact."""

import asyncio
from datetime import timedelta
from unittest.mock import patch

import pytest

from ase.adapters.bus.memory import InMemoryEventBus
from ase.adapters.store.memory import InMemoryEventStore
from ase.application.feeds.health import HealthRegistry
from ase.application.feeds.pipeline import Pipeline
from ase.application.feeds.scheduler import FeedScheduler
from feeds_helpers import NOW, FakeClock, FakeConnector, make_spec


@pytest.mark.parametrize(
    "source_id,expected",
    [
        ("firms_viirs_noaa20", 120),
        ("firms_viirs_noaa21", 120),
        ("firms_public_noaa20", 60),
        ("firms_public_noaa21", 60),
        ("firms_viirs_other", 60),
        ("test_source", 60),
    ],
)
@pytest.mark.parametrize("explicit", [None, timedelta(seconds=1), timedelta(0)])
async def test_fixed_firms_allowance_and_explicit_deadline(source_id, expected, explicit):
    connector = FakeConnector(make_spec(source_id))
    scheduler = FeedScheduler(
        [connector],
        Pipeline([]),
        InMemoryEventStore(),
        InMemoryEventBus(),
        HealthRegistry(),
        FakeClock(NOW),
        fetch_timeout=explicit,
    )
    original = asyncio.timeout
    with patch("ase.application.feeds.scheduler.asyncio.timeout", wraps=original) as deadline:
        await scheduler.poll_once(connector)
    deadline.assert_called_once_with(expected if explicit is None else explicit.total_seconds())
