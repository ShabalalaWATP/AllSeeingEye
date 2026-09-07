"""Secret URL boundary and task-local suppression of HTTP library diagnostics."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from urllib.parse import urlsplit

_protected: ContextVar[bool] = ContextVar("secret_feed_request", default=False)
# Actual emitting loggers in the locked HTTPX/HTTPcore dependencies. Parent filters
# do not apply to propagated child records. Recheck this list on transport upgrades.
HTTP_LOGGERS = (
    "httpx",
    "httpcore.connection",
    "httpcore.http11",
    "httpcore.http2",
    "httpcore.proxy",
    "httpcore.socks",
    "httpcore.connection_pool",
)


class _RequestLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not _protected.get()


_filter = _RequestLogFilter()


@contextmanager
def protect_http_logs() -> Iterator[None]:
    for name in HTTP_LOGGERS:
        logger = logging.getLogger(name)
        if _filter not in logger.filters:
            logger.addFilter(_filter)
    token = _protected.set(True)
    try:
        yield
    finally:
        _protected.reset(token)


@dataclass(frozen=True, slots=True)
class SecretFeedUrl:
    origin: str
    url: str = field(repr=False)

    def __post_init__(self) -> None:
        try:
            origin, target = urlsplit(self.origin), urlsplit(self.url)
            valid = (
                origin.scheme == target.scheme == "https"
                and bool(origin.hostname)
                and origin.hostname == target.hostname
                and (origin.port or 443) == (target.port or 443)
                and origin.port != 0
                and target.port != 0
                and not (origin.path or origin.query or origin.fragment)
                and not target.fragment
                and all(
                    part.username is None and part.password is None for part in (origin, target)
                )
                and all(32 < ord(char) < 127 for char in self.origin + self.url)
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Secret feed URL requires its exact HTTPS origin")
