"""Bounded, in-process Ask Eye evidence references, scoped to one account version."""

import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from ase.domain.assistant import AssistantContext
from ase.domain.errors import RateLimited
from ase.domain.users import User

CONTINUATION_TTL = timedelta(minutes=20)


@dataclass(frozen=True, slots=True)
class _Continuation:
    owner_id: UUID
    security_version: int
    expires_at: datetime
    context: AssistantContext


class AssistantCapacity:
    """Fail fast on model saturation and retain only small, expiring evidence packets."""

    def __init__(self, limit: int = 2) -> None:
        self.limit = limit
        self.active: set[UUID] = set()
        self._continuations: dict[str, _Continuation] = {}

    def find(self, actor: User, reference: str, now: datetime) -> AssistantContext | None:
        self._prune(now)
        row = self._continuations.get(reference)
        if (
            row is None
            or row.owner_id != actor.id
            or row.security_version != actor.security_version
        ):
            return None
        return row.context

    def remember(self, actor: User, context: AssistantContext, now: datetime) -> str:
        self._prune(now)
        owned = [key for key, row in self._continuations.items() if row.owner_id == actor.id]
        for key in owned[:-3]:
            self._continuations.pop(key, None)
        while len(self._continuations) >= 256:
            self._continuations.pop(next(iter(self._continuations)))
        reference = secrets.token_urlsafe(24)
        self._continuations[reference] = _Continuation(
            actor.id, actor.security_version, now + CONTINUATION_TTL, context
        )
        return reference

    def _prune(self, now: datetime) -> None:
        for key, row in tuple(self._continuations.items()):
            if row.expires_at <= now:
                self._continuations.pop(key, None)

    @contextmanager
    def reserve(self, actor_id: UUID) -> Iterator[None]:
        if actor_id in self.active or len(self.active) >= self.limit:
            raise RateLimited(5)
        self.active.add(actor_id)
        try:
            yield
        finally:
            self.active.discard(actor_id)
