"""The navigation-interference map, read only as cells and never written by a report."""

from collections.abc import Sequence
from typing import Protocol

from ase.domain.aviation import JamCell


class InterferenceCells(Protocol):
    def cells(self) -> Sequence[JamCell]:
        """Cells with enough aircraft-cell-hour observations in the retained window."""
        ...
