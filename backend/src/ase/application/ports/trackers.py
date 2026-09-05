"""Port for the curated conflict list the conflict tracker is built on."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from ase.domain.trackers import Conflict


class ConflictDirectory(Protocol):
    def all(self) -> Sequence[Conflict]: ...
    def get(self, conflict_id: str) -> Conflict | None: ...
