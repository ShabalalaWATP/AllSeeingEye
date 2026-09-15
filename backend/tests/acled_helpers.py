"""Synthetic ACLED OAuth fakes; never live account credentials or network."""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import SecretStr

from ase.adapters.feeds.acled_http import AcledForbidden, AcledRefreshRejected, AcledUnauthorised
from ase.adapters.feeds.http import FeedCredential, FeedFetchError
from ase.adapters.security.cipher import FernetCipher
from ase.application.ports.acled_credentials import StoredAcledRefreshToken

ENV_REFRESH = "synthetic-env-refresh-token-0001"
CIPHER = FernetCipher("k" * 40)


def grant(index: int, *, expires_in: int = 86400, **changes: Any) -> dict[str, Any]:
    return {
        "token_type": "Bearer",
        "expires_in": expires_in,
        "access_token": f"synthetic-access-{index:04d}",
        "refresh_token": f"synthetic-rotated-refresh-{index:04d}",
        **changes,
    }


class FakeAcledHttp:
    """Scripted token endpoint (grants or exceptions) and bearer reads."""

    def __init__(self, *grants: Any, reads: list[Any] | None = None, delay: float = 0) -> None:
        self.grants = list(grants)
        self.reads = list(reads or [])
        self.refreshed: list[str] = []
        self.read_with: list[str] = []
        self.delay = delay
        self.closed = False

    async def refresh(self, refresh_token: SecretStr) -> Any:
        self.refreshed.append(refresh_token.get_secret_value())
        if self.delay:
            await asyncio.sleep(self.delay)
        item = self.grants.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def read_json(self, url: str, credential: FeedCredential) -> Any:
        credential.require_origin(url)
        self.read_with.append(credential.authorization)
        item = self.reads.pop(0) if self.reads else {"status": 200, "data": []}
        if isinstance(item, Exception):
            raise item
        return item

    async def aclose(self) -> None:
        self.closed = True


class MemoryStore:
    def __init__(self, value: StoredAcledRefreshToken | None = None) -> None:
        self.value = value
        self.saves = 0
        self.fail_save = False

    async def load(self) -> StoredAcledRefreshToken | None:
        return self.value

    async def save(self, value: StoredAcledRefreshToken) -> None:
        if self.fail_save:
            raise RuntimeError("synthetic store failure")
        self.saves += 1
        self.value = value


def rejected() -> AcledRefreshRejected:
    return AcledRefreshRejected("ACLED refused the refresh token.")


def forbidden() -> AcledForbidden:
    return AcledForbidden("ACLED refused data access for this account.")


def unauthorised() -> AcledUnauthorised:
    return AcledUnauthorised("ACLED refused the access token.")


def transient() -> FeedFetchError:
    return FeedFetchError("ACLED authentication failed.")
