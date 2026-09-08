"""Persistence and bounded probing boundaries for the fixed NASA source."""

from typing import Protocol

from ase.domain.firms_credentials import FirmsCredential


class FirmsCredentialRepository(Protocol):
    async def get(self) -> FirmsCredential: ...
    async def save(self, value: FirmsCredential) -> None: ...


class FirmsProbe(Protocol):
    async def test(self, key: str, area: str) -> int: ...
