"""Optional diagnostics for feeds that can continue from validated cached inputs."""

from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable

from ase.application.ports.feeds import FeedConnector


class FeedDeferred(Exception):
    """No new upstream attempt was made, or requests now require operator attention."""

    def __init__(self, message: str, retry_at: datetime) -> None:
        super().__init__(message)
        self.retry_at = retry_at


class FeedBlocked(FeedDeferred):
    """The upstream refuses this client, registration or account tier until something changes.

    The message is fixed, server-authored text with no URL, credential or response body, so
    it may be shown to every signed-in user as the reason a source is not collecting.
    """


class FeedRateLimited(Exception):
    """The upstream asked for fewer requests; `retry_after` is its bounded wait, if stated."""

    def __init__(self, message: str, retry_after: timedelta | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


@runtime_checkable
class CoverageFeedConnector(FeedConnector, Protocol):
    """Expected coverage limits, independent of failed requests or cached-input fallback."""

    @property
    def coverage_warning(self) -> str | None: ...


@runtime_checkable
class DiagnosticFeedConnector(FeedConnector, Protocol):
    @property
    def warning(self) -> str | None: ...

    def request_retry(self) -> None:
        """An administrator has reviewed the failure; keep any minimum request interval."""
        ...
