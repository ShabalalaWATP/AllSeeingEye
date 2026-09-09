"""GNSS accuracy cells preserve observation time and count each aircraft once per hour."""

from datetime import timedelta, timezone

import pytest

from ase.adapters.store.memory import InMemoryEventStore
from ase.application.trackers.aviation import AviationService
from ase.domain.aviation import JamMap, is_bad
from ase.domain.events import Category, Point
from feeds_helpers import NOW, FakeClock, make_event


def observation(identifier="aircraft", nac_p=3, at=NOW):
    return make_event(
        identifier, category=Category.AVIATION, point=Point(5.2, 50.2), published_at=at
    ).with_changes(attributes={"icao_hex": identifier, "nac_p": nac_p})


@pytest.mark.parametrize("nac_p", [-1, 12, 3.5, True, "3", None])
def test_invalid_navigation_accuracy_is_not_classified(nac_p):
    assert is_bad(observation(nac_p=nac_p)) is None


def test_an_aircraft_cannot_be_both_good_and_bad_in_one_cell_hour():
    jam = JamMap()
    good = [observation(str(i), 9) for i in range(5)]
    jam.observe(good, NOW)
    jam.observe([observation("0", 3), observation("0", 9)], NOW)
    cell = jam.cells()[0]
    assert (cell.good, cell.bad) == (4, 1)


def test_repeated_sampling_does_not_move_observations_to_new_hours():
    jam = JamMap()
    rows = [observation(str(i)) for i in range(5)]
    jam.observe(rows, NOW)
    jam.observe(rows, NOW + timedelta(hours=1))
    assert jam.cells()[0].bad == 5
    assert jam.updated_at == NOW
    jam.observe([], NOW + timedelta(hours=2))
    assert jam.updated_at == NOW


def test_reads_expire_cells_even_when_the_sampler_stops():
    jam = JamMap()
    jam.observe([observation(str(i)) for i in range(5)], NOW)
    service = AviationService(InMemoryEventStore(), jam, FakeClock(NOW + timedelta(hours=26)))
    assert service.jam_cells() == []
    assert service.board({}, {}).jam_red == 0


def test_old_future_and_undated_observations_do_not_refresh_the_map():
    jam = JamMap()
    rows = [
        observation("old", at=NOW - timedelta(days=2)),
        observation("future", at=NOW + timedelta(hours=1)),
        observation("unknown", at=None),
        observation("naive", at=NOW.replace(tzinfo=None)),
    ]
    assert jam.observe(rows, NOW) == 0
    assert jam.updated_at is None


def test_hour_boundary_does_not_expire_an_observation_early():
    jam = JamMap()
    observed = NOW.replace(minute=59)
    jam.observe([observation(str(i), at=observed) for i in range(5)], observed)
    jam.prune(NOW + timedelta(days=1, minutes=30))
    assert jam.cells()[0].bad == 5
    jam.prune(NOW + timedelta(days=1, hours=1))
    assert jam.cells() == []


def test_budget_preserves_existing_observations_and_recovers_after_expiry():
    jam = JamMap(max_observations=5)
    jam.observe([observation(str(i), 9) for i in range(20)], NOW)
    assert jam.limited and jam.cells()[0].good == 5
    # Updates to known assignments remain possible, even at capacity.
    jam.observe([observation("0", 3)], NOW)
    assert (jam.cells()[0].good, jam.cells()[0].bad) == (4, 1)
    later = NOW + timedelta(hours=26)
    jam.observe([observation(str(i), at=later) for i in range(5)], later)
    assert not jam.limited and jam.cells()[0].bad == 5


def test_hour_buckets_use_utc_for_equivalent_offset_timestamps():
    jam = JamMap()
    observed = NOW.replace(minute=45)
    offset = timezone(timedelta(hours=5, minutes=30))
    rows = [observation(str(i), at=observed) for i in range(5)]
    jam.observe(rows, observed)
    jam.observe(
        [row.with_changes(published_at=observed.astimezone(offset)) for row in rows], observed
    )
    assert jam.cells()[0].bad == 5
    jam.prune((NOW + timedelta(days=1, minutes=45)).astimezone(offset))
    assert jam.cells()[0].bad == 5
