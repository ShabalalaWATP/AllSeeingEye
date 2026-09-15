"""A per-poll staging area for side effects that must only land when the poll succeeds.

Conditional-request validators are the motivating case: if a connector stores an ETag for
its first URL and a later URL in the same poll fails, the next poll would receive 304 for
the first URL and its items would never be published. Adapters stage such effects in the
active scope; the scheduler commits them after publication and discards them otherwise.
Outside any scope, callers apply their effects immediately.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_ACTIVE: ContextVar[PollScope | None] = ContextVar("ase_poll_scope", default=None)


class PollScope:
    def __init__(self) -> None:
        self._pending: dict[Hashable, Callable[[], None]] = {}

    def stage(self, key: Hashable, effect: Callable[[], None]) -> None:
        """Replace any effect already staged under the same key."""
        self._pending[key] = effect

    def commit(self) -> None:
        pending, self._pending = self._pending, {}
        for effect in pending.values():
            effect()

    def discard(self) -> None:
        self._pending.clear()


def active_poll_scope() -> PollScope | None:
    return _ACTIVE.get()


@contextmanager
def poll_scope() -> Iterator[PollScope]:
    """Staged effects are discarded unless the caller commits before leaving the block."""
    scope = PollScope()
    token = _ACTIVE.set(scope)
    try:
        yield scope
    finally:
        _ACTIVE.reset(token)
        scope.discard()
