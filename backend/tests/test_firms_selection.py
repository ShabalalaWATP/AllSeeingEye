"""Bounded global sampling preserves geography, recent records and measurement warnings."""

import asyncio
import threading
from datetime import timedelta

import pytest

from ase.adapters.feeds.firms import parse_firms
from ase.adapters.feeds.firms_parse_worker import parse_off_loop
from ase.adapters.feeds.firms_selection import MAX_DISPLAY_OBSERVATIONS, FirmsSelection
from ase.adapters.feeds.firms_sensors import NOAA20
from ase.adapters.feeds.http import FeedFetchError
from feeds_helpers import make_event
from test_firms_feed import NOW, ROW, payload


def test_more_than_thirty_thousand_valid_rows_keep_older_geographic_representative():
    rows = [{**ROW, "longitude": str(i / 100_000), "acq_time": "1200"} for i in range(30_001)]
    older = {**ROW, "latitude": "-70", "longitude": "150", "frp": "-0.53"}
    events = parse_firms(payload(*rows, older, older), NOW)
    assert len(events) == MAX_DISPLAY_OBSERVATIONS
    assert {e.attributes["collection_total_observations"] for e in events} == {30_002}
    assert {e.attributes["collection_returned_observations"] for e in events} == {10_000}
    remote = next(e for e in events if e.point.lat == -70)
    assert remote.attributes["reported_fire_radiative_power_mw"] == -0.53
    assert remote.attributes["fire_radiative_power_mw"] is None
    assert "Display sample" in remote.summary
    assert len({e.id for e in events}) == len(events)


def test_invalid_row_after_sample_capacity_is_still_rejected():
    rows = [{**ROW, "longitude": str(i / 100_000)} for i in range(20_001)]
    with pytest.raises(FeedFetchError, match="invalid observation"):
        parse_firms(payload(*rows, {**ROW, "latitude": "91"}), NOW)


def test_selection_heap_stays_bounded_and_small_batches_preserve_last_duplicate_values():
    selection = FirmsSelection()
    for index in range(30_000):
        selection.add(make_event(str(index), published_at=NOW + timedelta(seconds=index)))
    assert len(selection._latest) == 10_000
    assert len(selection._kept) == 10_000
    assert len(selection._cells) == 1
    selection.finish()
    assert not selection._kept and not selection._cells
    result = parse_firms(payload(ROW, {**ROW, "frp": "17"}), NOW)
    assert len(result) == 1
    assert result[0].attributes["fire_radiative_power_mw"] == 17
    assert result[0].attributes["collection_total_observations"] == 1
    assert result[0].attributes["collection_sampling_method"] == "All validated observations"


async def test_cancellation_retains_parse_slot_until_thread_finishes():
    entered, release, second_entered = threading.Event(), threading.Event(), threading.Event()

    def first(*args):
        entered.set()
        assert release.wait(5)
        return []

    def second(*args):
        second_entered.set()
        return []

    task = asyncio.create_task(parse_off_loop(first, b"", NOW, NOAA20))
    assert await asyncio.to_thread(entered.wait, 5)
    task.cancel()
    other = asyncio.create_task(parse_off_loop(second, b"", NOW, NOAA20))
    await asyncio.sleep(0)
    assert not second_entered.is_set()
    assert not task.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert await other == []
    assert second_entered.is_set()
