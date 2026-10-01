"""A retained-event store that reports when its contents last changed."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class GenerationalEventStore(Protocol):
    @property
    def generation(self) -> int:
        """Increases on every insert, replacement or removal, including expiry and regrades."""
        ...
