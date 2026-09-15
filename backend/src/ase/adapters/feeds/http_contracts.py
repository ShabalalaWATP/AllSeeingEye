"""Request-local feed credentials and safe fetch outcome types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from urllib.parse import urlsplit

import httpx

from ase.adapters.feeds.bounded_gzip import BoundedGzipError


class FeedFetchError(Exception):
    """A feed fetch failed; caller-visible text must not include private request data."""


class FeedTimeoutError(FeedFetchError, TimeoutError):
    """A feed exceeded its time limit without disclosing its request URL."""


class FeedHttpStatusError(FeedFetchError):
    """HTTP status without exposing an untrusted response body."""

    def __init__(self, status_code: int, url: str) -> None:
        super().__init__(f"HTTP {status_code} from {url}")
        self.status_code = status_code


class NotModified(Exception):
    """The upstream answered 304; no new data, rather than a failed fetch."""


def classify_fetch_error(exc: httpx.HTTPError | BoundedGzipError) -> FeedFetchError:
    if isinstance(exc, httpx.TimeoutException):
        return FeedTimeoutError("Feed request exceeded its time limit.")
    if isinstance(exc, BoundedGzipError):
        return FeedFetchError(str(exc))
    return FeedFetchError(f"{type(exc).__name__}: Feed request failed.")


def _https_origin(url: str) -> tuple[str, int] | None:
    try:
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or any(ord(char) < 33 or ord(char) > 126 for char in url)
        ):
            return None
        port = parts.port if parts.port is not None else 443
        return (parts.hostname.lower(), port) if port > 0 else None
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class FeedCredential:
    """Request-local authorisation bound to one exact HTTPS origin."""

    origin: str
    authorization: str = field(repr=False)
    header_name: Literal["Authorization", "x-ucdp-access-token", "X-API-Key"] = "Authorization"

    def __post_init__(self) -> None:
        if self.header_name not in ("Authorization", "x-ucdp-access-token", "X-API-Key"):
            raise ValueError("Unsupported credential header")
        try:
            parts = urlsplit(self.origin)
            valid = _https_origin(self.origin) is not None and not (
                parts.path or parts.query or parts.fragment
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("A credential requires an exact HTTPS origin without a path.")
        if (
            not self.authorization
            or len(self.authorization) > 8192
            or any(ord(char) < 32 or ord(char) > 126 for char in self.authorization)
        ):
            raise ValueError("Invalid request authorisation value.")

    def require_origin(self, url: str) -> None:
        if _https_origin(url) != _https_origin(self.origin):
            raise FeedFetchError("Request credential origin does not match the destination.")
