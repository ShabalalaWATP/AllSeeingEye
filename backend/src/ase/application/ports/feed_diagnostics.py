"""Optional diagnostics for feeds that can continue from validated cached inputs."""

from datetime import datetime
from typing import Protocol, runtime_checkable

from ase.application.ports.feeds import FeedConnector


class FeedDeferred(Exception):
    """No new upstream attempt was made, or requests now require operator attention."""

    def __init__(self, message: str, retry_at: datetime) -> None:
        super().__init__(message)
        self.retry_at = retry_at


@runtime_checkable
class DiagnosticFeedConnector(FeedConnector, Protocol):
    @property
    def warning(self) -> str | None: ...

    def request_retry(self) -> None:
        """An administrator has reviewed the failure; keep any minimum request interval."""
        ...
