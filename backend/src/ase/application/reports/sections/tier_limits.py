"""R04 synthesis ceilings; sparse evidence can yield fewer findings at any depth."""

from dataclasses import dataclass

from ase.domain.research import ResearchMode


@dataclass(frozen=True, slots=True)
class SynthesisLimits:
    judgements: int
    alternatives: int
    assumptions: int


_LIMITS = {
    ResearchMode.QUICK: SynthesisLimits(3, 2, 4),
    ResearchMode.DETAILED: SynthesisLimits(5, 3, 6),
    ResearchMode.ADVANCED: SynthesisLimits(8, 4, 8),
}
_LEGACY = SynthesisLimits(2, 2, 4)


def limits_for(mode: object) -> SynthesisLimits:
    """Unknown or historic scopes retain the strict old two-judgement ceiling."""
    if not isinstance(mode, str):
        return _LEGACY
    try:
        return _LIMITS[ResearchMode(mode)]
    except ValueError:
        return _LEGACY
