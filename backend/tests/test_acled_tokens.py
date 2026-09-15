"""ACLED refresh-token lifecycle: caching, early refresh, 401 retry, rotation and back-off."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import pytest
from pydantic import SecretStr
from structlog.testing import capture_logs

from acled_helpers import (
    CIPHER,
    ENV_REFRESH,
    FakeAcledHttp,
    MemoryStore,
    grant,
    rejected,
    transient,
    unauthorised,
)
from ase.adapters.feeds.acled_tokens import (
    REJECTED_BACKOFF,
    REVOKED_MESSAGE,
    AcledTokens,
    fingerprint,
)
from ase.adapters.feeds.conflict_acled import AcledConnector
from ase.adapters.feeds.http import FeedFetchError
from ase.adapters.security.cipher import FernetCipher
from ase.application.ports.acled_credentials import StoredAcledRefreshToken
from ase.application.ports.feed_diagnostics import FeedDeferred
from feeds_helpers import NOW, FakeClock

URL = "https://acleddata.com/api/acled/read?page=1"


def tokens(
    http: FakeAcledHttp,
    clock: FakeClock,
    store: MemoryStore | None = None,
    *,
    env: str = ENV_REFRESH,
    cipher: Any = CIPHER,
) -> AcledTokens:
    return AcledTokens(http, clock, SecretStr(env), store, cipher)  # type: ignore[arg-type]


async def test_first_use_exchanges_the_environment_token_and_reuses_the_cached_bearer() -> None:
    http, clock = FakeAcledHttp(grant(1)), FakeClock(NOW)
    provider = tokens(http, clock, MemoryStore())
    first = await provider.credential()
    clock.advance(timedelta(hours=23))
    assert await provider.credential() is first
    assert http.refreshed == [ENV_REFRESH]
    assert first.authorization == "Bearer synthetic-access-0001"
    assert "synthetic-access" not in repr(first)


async def test_refreshes_ten_minutes_before_expiry_with_the_rotated_token() -> None:
    http, clock = FakeAcledHttp(grant(1), grant(2)), FakeClock(NOW)
    provider = tokens(http, clock, MemoryStore())
    await provider.credential()
    clock.advance(timedelta(hours=23, minutes=49))
    assert (await provider.credential()).authorization.endswith("0001")
    clock.advance(timedelta(minutes=2))
    assert (await provider.credential()).authorization.endswith("0002")
    assert http.refreshed == [ENV_REFRESH, "synthetic-rotated-refresh-0001"]


async def test_a_401_refreshes_once_and_retries_the_read() -> None:
    http = FakeAcledHttp(grant(1), grant(2), reads=[unauthorised(), {"status": 200, "data": []}])
    provider = tokens(http, FakeClock(NOW), MemoryStore())
    assert await provider.get_json(URL) == {"status": 200, "data": []}
    assert len(http.refreshed) == 2
    assert http.read_with == ["Bearer synthetic-access-0001", "Bearer synthetic-access-0002"]


async def test_a_second_401_is_an_entitlement_error_without_further_refreshes() -> None:
    http = FakeAcledHttp(grant(1), grant(2), grant(3), reads=[unauthorised(), unauthorised()])
    provider = tokens(http, FakeClock(NOW), MemoryStore())
    with pytest.raises(FeedFetchError, match="entitlement"):
        await provider.get_json(URL)
    assert len(http.refreshed) == 2


async def test_concurrent_polls_share_a_single_refresh() -> None:
    http = FakeAcledHttp(grant(1), grant(2), delay=0.02)
    provider = tokens(http, FakeClock(NOW), MemoryStore())
    results = await asyncio.gather(*(provider.credential() for _ in range(5)))
    assert len(http.refreshed) == 1
    assert all(result is results[0] for result in results)


async def test_rotated_token_is_persisted_encrypted_and_reused_after_restart() -> None:
    store, clock = MemoryStore(), FakeClock(NOW)
    await tokens(FakeAcledHttp(grant(1)), clock, store).credential()
    assert store.value is not None and store.saves == 1
    assert "synthetic-rotated-refresh" not in store.value.encrypted
    assert CIPHER.decrypt(store.value.encrypted) == "synthetic-rotated-refresh-0001"
    assert store.value.environment_fingerprint == fingerprint(ENV_REFRESH)
    assert ENV_REFRESH not in store.value.environment_fingerprint
    assert store.value.encrypted not in repr(store.value)

    restarted = FakeAcledHttp(grant(2))
    await tokens(restarted, clock, store).credential()
    assert restarted.refreshed == ["synthetic-rotated-refresh-0001"]
    assert CIPHER.decrypt(store.value.encrypted) == "synthetic-rotated-refresh-0002"


async def test_a_new_environment_token_supersedes_the_stored_rotation() -> None:
    store = MemoryStore(
        StoredAcledRefreshToken(CIPHER.encrypt("old-rotated-token"), fingerprint("old-env"))
    )
    http = FakeAcledHttp(grant(1))
    await tokens(http, FakeClock(NOW), store).credential()
    assert http.refreshed == [ENV_REFRESH]
    assert store.value is not None
    assert store.value.environment_fingerprint == fingerprint(ENV_REFRESH)


async def test_unreadable_stored_token_falls_back_to_the_environment_token() -> None:
    other = FernetCipher("z" * 40)
    store = MemoryStore(StoredAcledRefreshToken(other.encrypt("rotated"), fingerprint(ENV_REFRESH)))
    http = FakeAcledHttp(grant(1))
    await tokens(http, FakeClock(NOW), store).credential()
    assert http.refreshed == [ENV_REFRESH]


async def test_rejected_refresh_token_defers_with_operator_message_and_backs_off() -> None:
    http, clock = FakeAcledHttp(rejected(), grant(1)), FakeClock(NOW)
    provider = tokens(http, clock, MemoryStore())
    with pytest.raises(FeedDeferred) as error:
        await provider.credential()
    assert str(error.value) == REVOKED_MESSAGE
    assert error.value.retry_at == NOW + REJECTED_BACKOFF
    clock.advance(timedelta(minutes=59))
    with pytest.raises(FeedDeferred, match="password grant"):
        await provider.credential()
    assert len(http.refreshed) == 1
    clock.advance(timedelta(minutes=2))
    assert (await provider.credential()).authorization.endswith("0001")
    assert len(http.refreshed) == 2


async def test_connector_surfaces_the_deferred_operator_message() -> None:
    http = FakeAcledHttp(rejected())
    connector = AcledConnector(
        http,  # type: ignore[arg-type]
        FakeClock(NOW),
        tokens=tokens(http, FakeClock(NOW), MemoryStore()),
    )
    with pytest.raises(FeedDeferred, match="ASE_ACLED_REFRESH_TOKEN"):
        await connector.fetch()


async def test_rejection_adopts_a_token_rotated_by_another_worker() -> None:
    store, clock = MemoryStore(), FakeClock(NOW)
    http = FakeAcledHttp(grant(1), rejected(), grant(3))
    provider = tokens(http, clock, store)
    await provider.credential()
    # Another worker rotates the chain and stores its token.
    store.value = StoredAcledRefreshToken(
        CIPHER.encrypt("worker-two-token"), fingerprint(ENV_REFRESH)
    )
    clock.advance(timedelta(hours=24))
    assert (await provider.credential()).authorization.endswith("0003")
    assert http.refreshed[1:] == ["synthetic-rotated-refresh-0001", "worker-two-token"]


async def test_transient_failure_keeps_a_valid_token_and_cools_down() -> None:
    http, clock = FakeAcledHttp(grant(1), transient(), transient()), FakeClock(NOW)
    provider = tokens(http, clock, MemoryStore())
    first = await provider.credential()
    clock.advance(timedelta(hours=23, minutes=55))
    assert await provider.credential() is first
    clock.advance(timedelta(minutes=1))
    assert await provider.credential() is first
    assert len(http.refreshed) == 2
    clock.advance(timedelta(minutes=10))
    with pytest.raises(FeedFetchError, match="cooldown"):
        await provider.credential()
    with pytest.raises(FeedFetchError, match="cooldown"):
        await provider.credential()
    assert len(http.refreshed) == 3


@pytest.mark.parametrize(
    "payload",
    [
        None,
        grant(1, token_type="mac"),
        grant(1, expires_in="86400"),
        grant(1, expires_in=10),
        grant(1, access_token="bad token"),
        grant(1, refresh_token={"x": 1}),
    ],
)
async def test_invalid_token_responses_are_rejected(payload: Any) -> None:
    provider = tokens(FakeAcledHttp(payload), FakeClock(NOW), MemoryStore())
    with pytest.raises(FeedFetchError, match="unavailable"):
        await provider.credential()


async def test_missing_rotation_keeps_the_current_refresh_token() -> None:
    store = MemoryStore()
    http = FakeAcledHttp(grant(1, refresh_token=None), grant(2, refresh_token=None))
    clock = FakeClock(NOW)
    provider = tokens(http, clock, store)
    await provider.credential()
    clock.advance(timedelta(days=1))
    await provider.credential()
    assert http.refreshed == [ENV_REFRESH, ENV_REFRESH] and store.saves == 0


async def test_without_encryption_rotation_stays_in_memory_with_a_warning() -> None:
    store = MemoryStore()
    with capture_logs() as logs:
        provider = tokens(FakeAcledHttp(grant(1)), FakeClock(NOW), store, cipher=FernetCipher(None))
    await provider.credential()
    assert store.value is None
    assert any(entry["event"] == "acled_refresh_rotation_in_memory" for entry in logs)


async def test_store_failure_is_logged_without_secrets(caplog: pytest.LogCaptureFixture) -> None:
    store = MemoryStore()
    store.fail_save = True
    with capture_logs() as logs, caplog.at_level(logging.DEBUG):
        provider = tokens(FakeAcledHttp(grant(1), rejected()), FakeClock(NOW), store)
        await provider.credential()
        provider.invalidate(await provider.credential())
        with pytest.raises(FeedDeferred):
            await provider.credential()
    assert any(entry["event"] == "acled_refresh_token_not_persisted" for entry in logs)
    rendered = repr(logs) + caplog.text
    for secret in (ENV_REFRESH, "synthetic-access", "synthetic-rotated-refresh"):
        assert secret not in rendered


def test_blank_environment_token_is_refused() -> None:
    with pytest.raises(ValueError, match="refresh token"):
        tokens(FakeAcledHttp(), FakeClock(NOW), MemoryStore(), env="  ")


async def test_close_releases_the_transport() -> None:
    http = FakeAcledHttp()
    await tokens(http, FakeClock(NOW), MemoryStore()).aclose()
    assert http.closed
