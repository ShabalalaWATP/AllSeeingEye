"""argon2id password hashing, run off the event loop with bounded concurrency."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import InvalidHashError, VerificationError

DEFAULT_CONCURRENCY = 2


class Argon2PasswordHasher:
    """Hash and verify in a small dedicated thread pool.

    Each argon2id call takes tens of milliseconds and 64 MiB, so running it on the
    event loop would stall every other request. The pool size is also the ceiling on
    concurrent hashing memory; further calls queue without allocating that memory.
    """

    def __init__(self, max_concurrency: int = DEFAULT_CONCURRENCY) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")
        # argon2id with the parameters pinned explicitly (OWASP-recommended profile) so a
        # library upgrade cannot weaken them silently; salts are random per hash.
        self._hasher = _Argon2(
            time_cost=3, memory_cost=65_536, parallelism=4, hash_len=32, salt_len=16
        )
        self._executor = ThreadPoolExecutor(
            max_workers=max_concurrency, thread_name_prefix="ase-argon2"
        )

    async def hash(self, password: str) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self.hash_blocking, password)

    async def verify(self, password_hash: str, password: str) -> bool:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor, self.verify_blocking, password_hash, password
        )

    def hash_blocking(self, password: str) -> str:
        """Synchronous hashing for start-up work that runs before requests are served."""
        return self._hasher.hash(password)

    def verify_blocking(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
