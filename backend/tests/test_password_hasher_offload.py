"""Password hashing runs off the event loop, with a bounded number of concurrent calls."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable

import pytest
from httpx import AsyncClient

from ase.adapters.security.hasher import Argon2PasswordHasher
from ase.container import Container

RELEASE_TIMEOUT_SECONDS = 5


class BlockingArgon2:
    """Stands in for the argon2 library and holds each call until the test releases it."""

    def __init__(self) -> None:
        self.release = threading.Event()
        self.threads: set[int] = set()
        self.active = 0
        self.peak = 0
        self._lock = threading.Lock()

    def verify(self, _password_hash: str, _password: str) -> bool:
        self._run()
        return False

    def hash(self, _password: str) -> str:
        self._run()
        return "hashed"

    def _run(self) -> None:
        with self._lock:
            self.threads.add(threading.get_ident())
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            self.release.wait(RELEASE_TIMEOUT_SECONDS)
        finally:
            with self._lock:
                self.active -= 1


async def _wait_for(condition: Callable[[], bool], timeout: float = 2.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not condition():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition was not met in time")
        await asyncio.sleep(0.005)


async def test_logins_in_progress_do_not_stall_other_requests(
    client: AsyncClient, container: Container, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocking = BlockingArgon2()
    monkeypatch.setattr(container.password_hasher, "_hasher", blocking)
    loop_thread = threading.get_ident()
    logins = [
        asyncio.create_task(
            client.post(
                "/api/auth/login",
                json={"email": f"nobody{index}@example.com", "password": "Wrong-Password-1"},
            )
        )
        for index in range(3)
    ]
    try:
        await _wait_for(lambda: blocking.active >= 2)
        # Hashing holds its worker threads, yet the loop still serves other requests.
        health = await asyncio.wait_for(client.get("/api/health"), timeout=2)
        assert health.status_code == 200
        assert not any(task.done() for task in logins)
        assert loop_thread not in blocking.threads
    finally:
        blocking.release.set()
    responses = await asyncio.gather(*logins)
    assert [response.status_code for response in responses] == [401, 401, 401]
    # The default pool runs two argon2 calls at once, so at most 128 MiB is in use.
    assert blocking.peak == 2


async def test_hasher_bounds_concurrent_calls() -> None:
    hasher = Argon2PasswordHasher(max_concurrency=3)
    blocking = BlockingArgon2()
    hasher._hasher = blocking  # type: ignore[assignment]
    try:
        calls = [asyncio.create_task(hasher.hash("value")) for _ in range(5)]
        calls += [asyncio.create_task(hasher.verify("digest", "value")) for _ in range(3)]
        await _wait_for(lambda: blocking.active == 3)
        await asyncio.sleep(0.05)
        assert blocking.active == 3
        blocking.release.set()
        results = await asyncio.gather(*calls)
    finally:
        blocking.release.set()
        hasher.close()
    assert results == ["hashed"] * 5 + [False] * 3
    assert blocking.peak == 3


async def test_real_argon2_round_trip_and_blocking_helpers() -> None:
    hasher = Argon2PasswordHasher(max_concurrency=1)
    try:
        digest = await hasher.hash("Correct-Horse-Battery-Staple")
        assert digest.startswith("$argon2id$")
        assert await hasher.verify(digest, "Correct-Horse-Battery-Staple")
        assert not await hasher.verify(digest, "wrong")
        assert hasher.verify_blocking(hasher.hash_blocking("other"), "other")
        assert not hasher.verify_blocking("not-a-hash", "other")
    finally:
        hasher.close()


def test_hasher_requires_at_least_one_worker() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        Argon2PasswordHasher(max_concurrency=0)


async def test_container_uses_configured_concurrency(container: Container) -> None:
    assert container.settings.password_hash_concurrency == 2
    assert container.password_hasher._executor._max_workers == 2
    assert container.hasher is container.password_hasher
