"""Evidence-bounded research length and packet size, independent of model settings.

The legacy quick/detailed values remain stable for saved requests and schedules.
Targets guide writing, never fabricate coverage or fail a sound shorter report.
"""

from dataclasses import dataclass

from ase.domain.research import ResearchMode


@dataclass(frozen=True, slots=True)
class ResearchDepth:
    label: str
    min_words: int
    max_words: int
    evidence_items: int
    per_source_cap: int
    output_tokens: int
    emphasis: str

    def guidance(self, *, share: float | None = None) -> str:
        target = f"{self.min_words:,} to {self.max_words:,}"
        instruction = (
            f"Research depth: {self.label}. Aim for {target} words across the complete "
            "report narrative, excluding references. "
        )
        if share is not None:
            # Reserve one fifth of the narrative for final judgements and context.
            # A dense packet still obeys the existing small-topic schema limits.
            lower = min(650, max(40, round(self.min_words * share * 0.8)))
            upper = min(800, max(lower, round(self.max_words * share * 0.8)))
            instruction += (
                f"This topic receives approximately {lower} to {upper} words in total across "
                "reporting and assessment, not the full-report allowance. "
            )
        return (
            instruction
            + self.emphasis
            + " These are indicative targets, not quotas. Evidence sufficiency and schema "
            "limits take precedence. Be shorter when evidence is thin. Never pad, repeat "
            "findings, invent facts or attach unrelated citations to reach a length target. "
            "Keep material uncertainty, contrary evidence and collection gaps at every depth."
        )


DEPTHS = {
    ResearchMode.QUICK: ResearchDepth(
        "Basic",
        750,
        1_350,
        24,
        6,
        9_000,
        "Prioritise the direct answer, the strongest relevant findings and essential caveats.",
    ),
    ResearchMode.DETAILED: ResearchDepth(
        "Deep",
        1_800,
        3_000,
        48,
        8,
        15_000,
        "Explain the evidence and reasoning by theme, compare source accounts and alternatives.",
    ),
    ResearchMode.ADVANCED: ResearchDepth(
        "Advanced",
        3_750,
        6_000,
        80,
        10,
        24_000,
        "Develop a comprehensive supported analysis: compare competing explanations, "
        "contradictions, source independence, chronology and implications where evidence permits.",
    ),
}


def depth_for(mode: object) -> ResearchDepth | None:
    """Only recognised, bounded scope values become trusted prompt instructions."""
    if not isinstance(mode, str):
        return None
    try:
        return DEPTHS[ResearchMode(mode)]
    except ValueError:
        return None
