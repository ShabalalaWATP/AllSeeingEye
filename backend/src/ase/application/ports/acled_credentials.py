"""Durable storage for the rotated ACLED OAuth refresh token (ciphertext only)."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StoredAcledRefreshToken:
    """`environment_fingerprint` identifies the environment token that seeded the chain."""

    encrypted: str = field(repr=False)
    environment_fingerprint: str


class AcledCredentialStore(Protocol):
    async def load(self) -> StoredAcledRefreshToken | None: ...
    async def save(self, value: StoredAcledRefreshToken) -> None: ...
