"""Bounded, transient originals and opaque choices; no permanent preservation claim."""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from ase.application.dto import AccessClaims
from ase.application.ports import Clock
from ase.domain.errors import NotFound, RateLimited
from ase.domain.sec_filings import SecFilingChoice, SecFilingPage

MAX_ORIGINAL_BYTES = 4 * 1024 * 1024
TTL = 900


@dataclass
class _Selected:
    choice: SecFilingChoice
    owner: UUID
    family: UUID
    security_version: int
    reserved: bool = False
    original: bytes | None = None


class BoundedSecSelections:
    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self._items: dict[UUID, _Selected] = {}

    def _expire(self) -> None:
        self._items = {
            key: value
            for key, value in self._items.items()
            if value.choice.expires_at > self.clock.now()
        }

    def issue(self, claims: AccessClaims, page: SecFilingPage) -> tuple[SecFilingChoice, ...]:
        self._expire()
        # Refresh only this session's unused picker page. Imported originals retain their TTL.
        self._items = {
            key: value
            for key, value in self._items.items()
            if value.family != claims.family_id or value.reserved
        }
        if len(self._items) + len(page.items) > 220:
            raise RateLimited(TTL)
        owned = sum(value.owner == claims.user_id for value in self._items.values())
        if owned + len(page.items) > 22:
            raise RateLimited(TTL)
        result = []
        for filing in page.items:
            choice = SecFilingChoice(uuid4(), filing, self.clock.now() + timedelta(seconds=TTL))
            self._items[choice.selection_id] = _Selected(
                choice, claims.user_id, claims.family_id, claims.security_version
            )
            result.append(choice)
        return tuple(result)

    def get(self, claims: AccessClaims, selection_id: UUID) -> SecFilingChoice:
        self._expire()
        value = self._items.get(selection_id)
        if value is None or (value.owner, value.family, value.security_version) != (
            claims.user_id,
            claims.family_id,
            claims.security_version,
        ):
            raise NotFound(
                "SEC selection expired or belongs to another session. Refresh the picker."
            )
        return value.choice

    def reserve_original(self, claims: AccessClaims, selection_id: UUID) -> None:
        self.get(claims, selection_id)
        value = self._items[selection_id]
        reserved = [row for row in self._items.values() if row.reserved]
        if (
            value.reserved
            or len(reserved) >= 8
            or sum(row.owner == claims.user_id for row in reserved) >= 2
        ):
            raise RateLimited(TTL)
        value.reserved = True

    def put_original(self, claims: AccessClaims, selection_id: UUID, data: bytes) -> None:
        self.get(claims, selection_id)
        value = self._items[selection_id]
        if not value.reserved or not data or len(data) > MAX_ORIGINAL_BYTES:
            raise ValueError("SEC original reservation or byte limit invalid")
        value.original = data

    def release_original(self, selection_id: UUID) -> None:
        value = self._items.get(selection_id)
        if value is not None:
            value.original = None
            value.reserved = False

    def original(self, claims: AccessClaims, selection_id: UUID) -> bytes:
        self.get(claims, selection_id)
        value = self._items[selection_id].original
        if value is None:
            raise NotFound("Import this filing before downloading its transient original.")
        return value
