"""Boundary for the native groundwave solver, no network is needed."""

from typing import Protocol

from ase.domain.groundwave import GroundwaveInput, GroundwaveSample


class GroundwaveSolver(Protocol):
    def calculate(self, inputs: GroundwaveInput) -> tuple[GroundwaveSample, ...]: ...
