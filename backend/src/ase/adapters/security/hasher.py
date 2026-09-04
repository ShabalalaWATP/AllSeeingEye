"""argon2id password hashing."""

from __future__ import annotations

from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import InvalidHashError, VerificationError


class Argon2PasswordHasher:
    def __init__(self) -> None:
        # argon2id with the parameters pinned explicitly (OWASP-recommended profile) so a
        # library upgrade cannot weaken them silently; salts are random per hash.
        self._hasher = _Argon2(
            time_cost=3, memory_cost=65_536, parallelism=4, hash_len=32, salt_len=16
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False
