"""Per-account admission for semantic search, so one caller cannot hold everyone's slot."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from ase.domain.errors import RateLimited

# Embedding calls per account and per process in each window. The per-account
# allowance is a tenth of the shared one, so at least ten accounts are needed to
# exhaust the shared backstop, which still bounds the installation's model spend.
# Indexing sends eight reports per call, so one account can index 240 reports an hour.
EMBEDDING_CALLS_PER_USER = 30
EMBEDDING_CALLS_GLOBAL = 300
EMBEDDING_WINDOW_SECONDS = 3600
# Concurrent semantic queries across the process, at most one per account.
MAX_CONCURRENT_QUERIES = 4


class SearchSlots:
    """Admit one semantic query per account, within a small shared concurrency cap.

    The event loop is single-threaded and admission never awaits, so checking and
    claiming a slot cannot interleave with another request.
    """

    def __init__(self, shared: int = MAX_CONCURRENT_QUERIES) -> None:
        self._shared = shared
        self._active: set[UUID] = set()

    @asynccontextmanager
    async def claim(self, user_id: UUID) -> AsyncIterator[None]:
        if user_id in self._active or len(self._active) >= self._shared:
            raise RateLimited(1)
        self._active.add(user_id)
        try:
            yield
        finally:
            self._active.discard(user_id)
