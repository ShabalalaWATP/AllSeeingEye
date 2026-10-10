"""Operational access to the packaged conflict catalogue, separate from inventory."""

from collections.abc import Sequence

from ase.application.ports.trackers import ConflictDirectory
from ase.domain.source_licences import SourceLicencePolicy
from ase.domain.trackers import Conflict


class LicensedConflicts:
    def __init__(self, directory: ConflictDirectory, licences: SourceLicencePolicy) -> None:
        self._directory, self._licences = directory, licences

    def all(self) -> Sequence[Conflict]:
        self._licences.require("reference:conflicts")
        return self._directory.all()

    def get(self, conflict_id: str) -> Conflict | None:
        self._licences.require("reference:conflicts")
        return self._directory.get(conflict_id)
