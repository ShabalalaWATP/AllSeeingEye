"""Satellite recovery must preserve provider limits and honest prediction freshness."""

from datetime import timedelta
from pathlib import Path

import pytest

from ase.adapters.feeds.http import FeedFetchError, FeedHttpStatusError
from ase.adapters.feeds.satellite_http import ElementsNotUpdated
from ase.adapters.feeds.satellites import ACTIVE_SATELLITES, SatelliteConnector
from ase.application.feeds.health import SourceStatus
from feeds_helpers import NOW, FakeClock, FakeHttp
from test_pipeline_and_scheduler import build_scheduler
from test_satellite_catalogues import csv_catalogue, elements


class FailingHttp(FakeHttp):
    async def get_text(self, url: str, *, conditional: bool = True) -> str:
        self.requests.append(url)
        raise FeedFetchError("HTTP 403 from public catalogue")


async def test_restart_reuses_elements_without_another_download(tmp_path: Path) -> None:
    clock = FakeClock(NOW)
    http = FakeHttp({"gp.php": csv_catalogue([elements()])})
    first = SatelliteConnector(http, clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    before = (await first.fetch())[0]
    clock.advance(timedelta(minutes=2))
    restarted = SatelliteConnector(http, clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    after = (await restarted.fetch())[0]
    assert len(http.requests) == 1
    assert after.attributes["position_at"] != before.attributes["position_at"]
    assert after.attributes["elements_downloaded_at"] == NOW.isoformat()


async def test_failure_and_cooldown_survive_restart(tmp_path: Path) -> None:
    http, clock = FailingHttp(), FakeClock(NOW)
    first = SatelliteConnector(http, clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    with pytest.raises(FeedFetchError):
        await first.fetch()
    clock.advance(timedelta(minutes=2))
    restarted = SatelliteConnector(http, clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    with pytest.raises(FeedFetchError):
        await restarted.fetch()
    assert len(http.requests) == 1


async def test_failed_refresh_keeps_usable_elements_and_exposes_warning(tmp_path: Path) -> None:
    clock = FakeClock(NOW)
    good = SatelliteConnector(
        FakeHttp({"gp.php": csv_catalogue([elements()])}),
        clock,
        ACTIVE_SATELLITES,
        cache_dir=tmp_path,
    )
    assert len(await good.fetch()) == 1
    clock.advance(timedelta(hours=2))
    http = FailingHttp()
    failed = SatelliteConnector(http, clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    event = (await failed.fetch())[0]
    assert event.attributes["element_refresh_failed"] is True
    assert event.attributes["elements_downloaded_at"] == NOW.isoformat()
    assert "403" in failed.warning
    clock.advance(timedelta(minutes=2))
    restarted = SatelliteConnector(http, clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    current = (await restarted.fetch())[0]
    assert current.attributes["position_at"] == clock.now().isoformat()
    assert current.attributes["element_refresh_failed"] is True
    assert len(http.requests) == 1


def test_stationary_position_hash_still_refreshes_prediction_time(monkeypatch) -> None:
    connector = SatelliteConnector(FakeHttp(), FakeClock(NOW))
    first = connector._to_event(elements(), NOW)
    assert first is not None
    monkeypatch.setattr(
        "ase.adapters.feeds.satellites.subpoint",
        lambda r, when: (first.point, first.attributes["altitude_km"]),
    )
    later = connector._to_event(elements(), NOW + timedelta(minutes=2))
    assert later is not None
    assert later.content_hash != first.content_hash


async def test_expired_cache_never_extends_orbital_epoch(tmp_path: Path) -> None:
    clock = FakeClock(NOW)
    connector = SatelliteConnector(
        FakeHttp({"gp.php": csv_catalogue([elements()])}),
        clock,
        ACTIVE_SATELLITES,
        cache_dir=tmp_path,
    )
    await connector.fetch()
    clock.advance(timedelta(days=15))
    restarted = SatelliteConnector(FailingHttp(), clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    assert await restarted.fetch() == []
    assert "expired" in restarted.warning


async def test_invalid_refresh_retains_previous_good_catalogue(tmp_path: Path) -> None:
    clock = FakeClock(NOW)
    http = FakeHttp({"gp.php": csv_catalogue([elements()])})
    connector = SatelliteConnector(http, clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    await connector.fetch()
    clock.advance(timedelta(hours=2))
    http.payloads = {"gp.php": "<html>Temporary error</html>"}
    assert len(await connector.fetch()) == 1
    assert "missing orbital fields" in connector.warning
    assert connector._catalogue.state.fetched_at == NOW


@pytest.mark.parametrize("changes", [{"EPOCH": "bad"}, {"MEAN_MOTION": "bad"}])
async def test_plausible_but_invalid_orbits_cannot_replace_good_cache(tmp_path: Path, changes):
    clock = FakeClock(NOW)
    http = FakeHttp({"gp.php": csv_catalogue([elements()])})
    connector = SatelliteConnector(http, clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    await connector.fetch()
    clock.advance(timedelta(hours=2))
    http.payloads = {"gp.php": csv_catalogue([elements(**changes)])}
    assert len(await connector.fetch()) == 1
    assert "no usable orbital elements" in connector.warning
    restarted = SatelliteConnector(http, clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    assert len(await restarted.fetch()) == 1
    assert restarted._catalogue.state.fetched_at == NOW


async def test_scheduler_keeps_cached_positions_but_reports_degraded(tmp_path: Path) -> None:
    clock = FakeClock(NOW)
    initial = SatelliteConnector(
        FakeHttp({"gp.php": csv_catalogue([elements()])}),
        clock,
        ACTIVE_SATELLITES,
        cache_dir=tmp_path,
    )
    await initial.fetch()
    clock.advance(timedelta(hours=2))
    connector = SatelliteConnector(FailingHttp(), clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    scheduler, store, _, health = build_scheduler([connector], clock)
    result = await scheduler.poll_once(connector)
    assert result.ok and result.fetched == 1
    assert store.stats().total == 1
    entry = health.get(ACTIVE_SATELLITES.id)
    assert entry.status is SourceStatus.DEGRADED
    assert "403" in entry.last_error
    assert entry.next_poll_at == clock.now() + timedelta(minutes=2)


async def test_cooldown_is_not_a_series_of_failed_network_calls(tmp_path: Path) -> None:
    clock, http = FakeClock(NOW), FailingHttp()
    connector = SatelliteConnector(http, clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    scheduler, _, _, health = build_scheduler([connector], clock)
    for _ in range(10):
        assert not (await scheduler.poll_once(connector)).ok
        clock.advance(timedelta(minutes=2))
    entry = health.get(ACTIVE_SATELLITES.id)
    assert entry.status is SourceStatus.DEGRADED
    assert entry.consecutive_failures == 0
    assert entry.next_poll_at == NOW + timedelta(hours=2)
    assert len(http.requests) == 1


async def test_access_refusal_persists_until_operator_retry(tmp_path: Path) -> None:
    class BlockedHttp(FakeHttp):
        async def get_text(self, url: str, *, conditional: bool = True) -> str:
            self.requests.append(url)
            raise FeedHttpStatusError(403, url)

    clock, http = FakeClock(NOW), BlockedHttp()
    connector = SatelliteConnector(http, clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    with pytest.raises(FeedFetchError, match="downloads paused"):
        await connector.fetch()
    clock.advance(timedelta(hours=3))
    restarted = SatelliteConnector(http, clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    with pytest.raises(FeedFetchError):
        await restarted.fetch()
    assert len(http.requests) == 1
    scheduler, _, _, _ = build_scheduler([restarted], clock)
    scheduler.resume(ACTIVE_SATELLITES.id)
    with pytest.raises(FeedFetchError):
        await restarted.fetch()
    assert len(http.requests) == 2
    restarted.request_retry()
    with pytest.raises(FeedFetchError):
        await restarted.fetch()
    assert len(http.requests) == 2


@pytest.mark.parametrize("warm", [True, False])
async def test_unchanged_response_reuses_cache_or_waits_for_next_update(tmp_path: Path, warm):
    class UnchangedHttp(FakeHttp):
        async def get_text(self, url: str, *, conditional: bool = True) -> str:
            self.requests.append(url)
            raise ElementsNotUpdated("CelesTrak has no newer orbital elements yet")

    clock = FakeClock(NOW)
    if warm:
        initial = SatelliteConnector(
            FakeHttp({"gp.php": csv_catalogue([elements()])}),
            clock,
            ACTIVE_SATELLITES,
            cache_dir=tmp_path,
        )
        await initial.fetch()
        clock.advance(timedelta(hours=2))
    http = UnchangedHttp()
    connector = SatelliteConnector(http, clock, ACTIVE_SATELLITES, cache_dir=tmp_path)
    if warm:
        assert len(await connector.fetch()) == 1
        assert connector.warning is None
        assert connector._catalogue.state.fetched_at == NOW
    else:
        with pytest.raises(FeedFetchError, match="no local elements"):
            await connector.fetch()
    assert not connector._catalogue.state.blocked
    assert connector._catalogue.state.retry_at == clock.now() + timedelta(hours=2)


async def test_unwritable_cache_does_not_make_a_request(tmp_path: Path, monkeypatch):
    def cannot_save(*args):
        raise OSError("Unavailable")

    http = FakeHttp()
    connector = SatelliteConnector(http, FakeClock(NOW), ACTIVE_SATELLITES, cache_dir=tmp_path)
    monkeypatch.setattr(connector._catalogue.cache, "save", cannot_save)
    with pytest.raises(FeedFetchError, match="not writable"):
        await connector.fetch()
    assert http.requests == []
