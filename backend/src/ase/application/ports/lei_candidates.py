"""Public registry candidates never imply a confirmed subject identity."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class LeiCandidate:
    lei: str
    name: str
    jurisdiction: str
    status: str


class LeiCandidateLookup(Protocol):
    async def search(self, name: str, country: str | None) -> tuple[LeiCandidate, ...]: ...
