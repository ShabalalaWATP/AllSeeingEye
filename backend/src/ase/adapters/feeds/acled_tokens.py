"""ACLED OAuth refresh-token lifecycle: cached bearer, single-flight refresh, durable rotation.

The operator runs ACLED's password grant once and supplies only the refresh token. Each
refresh returns a new refresh token; it is stored encrypted with a fingerprint of the
environment token that seeded the chain, so a newly pasted environment token supersedes
the stored one. Tokens, response bodies and upstream error text are never logged.
"""

import asyncio
import hashlib
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from pydantic import SecretStr

from ase.adapters.feeds.acled_http import (
    ORIGIN,
    AcledForbidden,
    AcledHttpClient,
    AcledRefreshRejected,
    AcledUnauthorised,
)
from ase.adapters.feeds.http import FeedCredential, FeedFetchError
from ase.application.ports import Clock
from ase.application.ports.acled_credentials import AcledCredentialStore, StoredAcledRefreshToken
from ase.application.ports.feed_diagnostics import FeedBlocked, FeedDeferred
from ase.application.ports.llm import SecretCipher

log = structlog.get_logger(__name__)

EARLY_REFRESH = timedelta(minutes=10)
REJECTED_BACKOFF = timedelta(hours=1)
ENTITLEMENT_RECHECK = timedelta(hours=12)
FAILURE_BACKOFF = timedelta(minutes=5)
MAX_LIFETIME_SECONDS = 86400
REVOKED_MESSAGE = (
    "ACLED refresh token expired or revoked; run the password grant again and update "
    "ASE_ACLED_REFRESH_TOKEN"
)
UNAVAILABLE_MESSAGE = "ACLED authentication unavailable; retrying after a short cooldown."
ENTITLEMENT_MESSAGE = (
    "ACLED accepted the credentials but refused data access (HTTP 403). API access needs a "
    "myACLED Research, Partner or Enterprise tier; accounts registered with a public email "
    "address get Open access, which has no API. The application rechecks every 12 hours."
)
_TOKEN = re.compile(r"[A-Za-z0-9._~+/-]+=*")


def fingerprint(token: str) -> str:
    """Identifies an environment token without storing it; tokens are high-entropy."""
    return hashlib.sha256(b"ase:acled-refresh-token:v1:" + token.encode("utf-8")).hexdigest()


def _valid_token(value: object) -> str | None:
    if isinstance(value, str) and 1 <= len(value) <= 8000 and _TOKEN.fullmatch(value):
        return value
    return None


class AcledTokens:
    def __init__(
        self,
        http: AcledHttpClient,
        clock: Clock,
        environment_token: SecretStr,
        store: AcledCredentialStore | None,
        cipher: SecretCipher,
    ) -> None:
        self._http, self._clock, self._cipher = http, clock, cipher
        self._environment = environment_token.get_secret_value().strip()
        if not self._environment:
            raise ValueError("ACLED requires a refresh token.")
        self._fingerprint = fingerprint(self._environment)
        self._store = store if store is not None and cipher.available else None
        if self._store is None:
            log.warning(
                "acled_refresh_rotation_in_memory",
                detail="Set ASE_ENCRYPTION_KEY so rotated ACLED refresh tokens survive restarts.",
            )
        self._refresh: str | None = None
        self._credential: FeedCredential | None = None
        self._expires_at = self._refresh_at = datetime.min.replace(tzinfo=UTC)
        self._retry_at: datetime | None = None
        self._rejected = False
        self._lock = asyncio.Lock()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def get_json(self, url: str) -> Any:
        """A 401 refreshes the access token once and retries; a second 401 is an error.

        A 403 is the account's entitlement, not the token, so it is reported as a block.
        """
        credential = await self.credential()
        try:
            return await self._http.read_json(url, credential)
        except AcledUnauthorised:
            self.invalidate(credential)
        except AcledForbidden:
            raise self._entitlement_block() from None
        credential = await self.credential()
        try:
            return await self._http.read_json(url, credential)
        except AcledForbidden:
            raise self._entitlement_block() from None
        except AcledUnauthorised:
            self.invalidate(credential)
            raise FeedFetchError(
                "ACLED refused a freshly refreshed access token; check account entitlement."
            ) from None

    def _entitlement_block(self) -> FeedBlocked:
        return FeedBlocked(ENTITLEMENT_MESSAGE, self._clock.now() + ENTITLEMENT_RECHECK)

    def invalidate(self, credential: FeedCredential) -> None:
        """Never let an older failed request discard a newer refreshed token."""
        if self._credential is credential:
            self._credential = None

    async def credential(self) -> FeedCredential:
        async with self._lock:
            now = self._clock.now()
            cached = self._credential if self._credential and now < self._expires_at else None
            if cached is not None and now < self._refresh_at:
                return cached
            if self._retry_at is not None and now < self._retry_at:
                if cached is not None:
                    return cached
                raise self._cooldown_error()
            try:
                return await self._exchange(now)
            except (FeedDeferred, FeedFetchError):
                # An early refresh that fails keeps a still-valid access token in use.
                if cached is not None:
                    return cached
                raise

    async def _exchange(self, now: datetime) -> FeedCredential:
        refresh = await self._current_refresh_token()
        data: Any = None
        for attempt in range(2):
            try:
                data = await self._http.refresh(SecretStr(refresh))
                break
            except AcledRefreshRejected:
                # Another worker may have rotated the chain; adopt its stored token once.
                newer = await self._stored_token() if attempt == 0 else None
                if newer is None or newer == refresh:
                    raise self._cool_down(now, rejected=True) from None
                self._refresh = refresh = newer
            except Exception:
                raise self._cool_down(now, rejected=False) from None
        parsed = self._parse(data)
        if parsed is None:
            raise self._cool_down(now, rejected=False)
        access, lifetime, rotated = parsed
        self._expires_at = now + lifetime
        self._refresh_at = self._expires_at - min(EARLY_REFRESH, lifetime / 2)
        self._credential = FeedCredential(ORIGIN, f"Bearer {access}")
        self._retry_at, self._rejected = None, False
        if rotated is not None and rotated != refresh:
            self._refresh = rotated
            await self._persist(rotated)
        return self._credential

    @staticmethod
    def _parse(data: Any) -> tuple[str, timedelta, str | None] | None:
        if not isinstance(data, dict):
            return None
        access, expires = _valid_token(data.get("access_token")), data.get("expires_in")
        token_type = data.get("token_type")
        rotated = data.get("refresh_token")
        if (
            access is None
            or not isinstance(token_type, str)
            or token_type.lower() != "bearer"
            or type(expires) is not int
            or not 60 <= expires <= 14 * MAX_LIFETIME_SECONDS
            or (rotated is not None and _valid_token(rotated) is None)
        ):
            return None
        return access, timedelta(seconds=min(expires, MAX_LIFETIME_SECONDS)), rotated

    def _cool_down(self, now: datetime, *, rejected: bool) -> Exception:
        self._retry_at = now + (REJECTED_BACKOFF if rejected else FAILURE_BACKOFF)
        self._rejected = rejected
        log.warning("acled_refresh_failed", rejected=rejected, retry_at=self._retry_at.isoformat())
        return self._cooldown_error()

    def _cooldown_error(self) -> Exception:
        if self._rejected and self._retry_at is not None:
            return FeedDeferred(REVOKED_MESSAGE, self._retry_at)
        return FeedFetchError(UNAVAILABLE_MESSAGE)

    async def _current_refresh_token(self) -> str:
        if self._refresh is None:
            self._refresh = await self._stored_token() or self._environment
        return self._refresh

    async def _stored_token(self) -> str | None:
        """The persisted rotation, unless a different environment token has been supplied."""
        if self._store is None:
            return None
        try:
            stored = await self._store.load()
            if stored is None or stored.environment_fingerprint != self._fingerprint:
                return None
            return _valid_token(self._cipher.decrypt(stored.encrypted))
        except Exception:
            log.warning("acled_refresh_token_store_unreadable")
            return None

    async def _persist(self, token: str) -> None:
        if self._store is None:
            return
        try:
            await self._store.save(
                StoredAcledRefreshToken(self._cipher.encrypt(token), self._fingerprint)
            )
        except Exception:
            log.warning(
                "acled_refresh_token_not_persisted",
                detail="The rotated token is kept in memory only until the next restart.",
            )
