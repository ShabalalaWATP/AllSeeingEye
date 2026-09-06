"""In-memory authoritative identity and extraction doubles for private input tests."""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from ase.adapters.research_imports import events_from_extraction, extract_upload
from ase.adapters.research_inputs.memory import BoundedResearchInputStore
from ase.application.access import AccessPolicy
from ase.application.ports.research_inputs import InputExtraction
from ase.application.research.inputs import ImportResearchInput
from ase.domain.users import Role, User
from helpers import FakeClock

NOW = datetime(2026, 9, 6, 12, tzinfo=UTC)


def actor() -> User:
    return User(
        uuid4(),
        "fixture@example.invalid",
        "Fixture",
        Role.USER,
        True,
        None,
        0,
        None,
        None,
        NOW,
        None,
    )


def extracted(
    filename: str = "notes.txt", text: bytes = b"Original factual claim."
) -> InputExtraction:
    result = extract_upload(text, filename)
    return InputExtraction(
        result.filename,
        result.media_type,
        result.sha256,
        events_from_extraction(result, NOW),
        result.limitations,
    )


class Identity:
    def __init__(self, user: User) -> None:
        self.current = replace(user)
        self.locked = False

    async def get_by_id(self, user_id: UUID) -> User | None:
        return replace(self.current) if user_id == self.current.id else None

    async def lock_by_id(self, user_id: UUID) -> User | None:
        return await self.get_by_id(user_id)

    async def lock_administration(self) -> None:
        self.locked = True

    async def list_visible(self, *args: Any, **kwargs: Any) -> list[Any]:
        return []

    async def memberships_for_user(self, *args: Any) -> list[Any]:
        return []


class Uow:
    def __init__(self, identity: Identity) -> None:
        self.identity, self.rollbacks = identity, 0

    async def rollback(self) -> None:
        self.identity.locked = False
        self.rollbacks += 1

    async def commit(self) -> None:
        raise AssertionError("Private input extraction must not persist data.")


class Limiter:
    def __init__(self) -> None:
        self.hits: dict[str, int] = {}

    def hit(self, key: str, limit: int, window_seconds: int) -> int | None:
        self.hits[key] = self.hits.get(key, 0) + 1
        return window_seconds if self.hits[key] > limit else None


class Extractor:
    def __init__(self, identity: Identity) -> None:
        self.identity = identity
        self.calls = 0
        self.error: BaseException | None = None
        self.change: dict[str, Any] = {}

    async def extract(self, data: bytes, filename: str, captured_at: datetime) -> InputExtraction:
        assert not self.identity.locked
        self.calls += 1
        self.identity.current = replace(self.identity.current, **self.change)
        if self.error:
            raise self.error
        return extracted(filename, data)


class Harness:
    def __init__(self) -> None:
        self.actor = actor()
        self.clock = FakeClock(NOW)
        self.identity = Identity(self.actor)
        self.uow = Uow(self.identity)
        self.extractor = Extractor(self.identity)
        self.store = BoundedResearchInputStore(self.clock)
        self.service = ImportResearchInput(
            AccessPolicy(self.identity, self.identity),
            self.extractor,
            self.store,
            self.clock,
            Limiter(),
            self.uow,
        )
