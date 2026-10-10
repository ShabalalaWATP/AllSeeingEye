"""Immutable installation licence decisions, separate from credentials and admin toggles."""

from collections.abc import Iterable
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from ase.domain.errors import Forbidden

CommercialUse = Literal["allowed", "forbidden", "licence_required"]
LICENCE_UNAVAILABLE = "Not available on this installation due to licence terms"


@dataclass(frozen=True, slots=True)
class SourceLicence:
    source_id: str
    commercial_use: CommercialUse
    attribution_required: bool
    licence_ref: str


@dataclass(frozen=True, slots=True)
class SourceLicenceDecision:
    commercial_use: CommercialUse
    attribution_required: bool
    licence_ref: str
    available: bool
    acknowledged: bool
    reason: str


class SourceLicencePolicy:
    """Operator acknowledgement records permission; it cannot override a prohibition."""

    def __init__(
        self,
        entries: Iterable[SourceLicence],
        *,
        commercial_use: bool = False,
        acknowledgements: frozenset[str] = frozenset(),
    ) -> None:
        self._entries = MappingProxyType({entry.source_id: entry for entry in entries})
        self._commercial_use = commercial_use
        self._acknowledgements = acknowledgements

    @property
    def commercial_use(self) -> bool:
        return self._commercial_use

    def validate_ids(self, source_ids: Iterable[str]) -> None:
        if missing := set(source_ids) - self._entries.keys():
            raise ValueError(f"Missing source licence metadata: {', '.join(sorted(missing))}")

    def decision(self, source_id: str) -> SourceLicenceDecision:
        entry = self._entries.get(source_id)
        status = entry.commercial_use if entry else "licence_required"
        acknowledged = (
            entry is not None
            and status == "licence_required"
            and (source_id in self._acknowledgements)
        )
        available = not self._commercial_use or (
            entry is not None
            and (status == "allowed" or (status == "licence_required" and acknowledged))
        )
        if not self._commercial_use:
            reason = "Commercial source mode is off."
        elif status == "forbidden":
            reason = "The reviewed source terms prohibit this commercial use."
        elif not available:
            reason = "Explicit permission and a per-source operator acknowledgement are required."
        elif acknowledged:
            reason = "The operator has acknowledged permission for this exact source."
        else:
            reason = "Commercial use is permitted subject to the recorded licence conditions."
        return SourceLicenceDecision(
            status,
            entry.attribution_required if entry else True,
            entry.licence_ref if entry else "docs/SOURCE_LICENCES.md",
            available,
            acknowledged,
            reason,
        )

    def allowed(self, source_id: str) -> bool:
        return self.decision(source_id).available

    def require(self, source_id: str) -> None:
        if not self.allowed(source_id):
            raise Forbidden(LICENCE_UNAVAILABLE)
