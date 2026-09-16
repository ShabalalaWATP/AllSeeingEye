"""The direction call's PIR, SIRs and EEIs as the shared intelligence-requirement type.

A pinned Research Brief already states requirements. For a free-form ask the direction
call derives them, and they steer source allocation and evidence ranking in the same
shape. The translation is pure: no text is rewritten and nothing is invented.
"""

from __future__ import annotations

from ase.domain.direction import Direction
from ase.domain.research_brief_values import IntelligenceRequirement

# The brief contract accepts at most twelve requirements at priorities one to twelve.
MAX_DERIVED_REQUIREMENTS = 12


def direction_requirements(direction: Direction | None) -> tuple[IntelligenceRequirement, ...]:
    """PIR first, then SIRs as required, then EEIs as optional, within the brief bounds."""
    if direction is None:
        return ()
    rows: list[tuple[str, str, bool]] = [("PIR-1", direction.pir, True)]
    rows.extend(
        (f"SIR-{index}", text, True) for index, text in enumerate(direction.sirs, 1) if text
    )
    rows.extend(
        (f"EEI-{index}", text, False) for index, text in enumerate(direction.eeis, 1) if text
    )
    return tuple(
        IntelligenceRequirement(
            identifier,
            question[:500],
            required,
            min(MAX_DERIVED_REQUIREMENTS, position),
        )
        for position, (identifier, question, required) in enumerate(
            rows[:MAX_DERIVED_REQUIREMENTS], 1
        )
        if question.strip()
    )


def effective_requirements(
    canonical: tuple[IntelligenceRequirement, ...], direction: Direction | None
) -> tuple[IntelligenceRequirement, ...]:
    """A pinned brief wins; otherwise the direction call supplies the requirements."""
    return canonical or direction_requirements(direction)
