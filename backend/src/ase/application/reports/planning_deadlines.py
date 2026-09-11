"""Planning deadlines match transport bounds while preserving the collection allowance."""

from math import isfinite

from ase.domain.llm import ReasoningEffort

# The existing research_plan/research_continuation transport budget is 120 seconds.
# Initial planning precedes collection; follow-up planning shares collection time.
DURABLE_PLANNING_SECONDS = 120.0


def continuation_seconds(
    remaining: float, effort: ReasoningEffort | None, *, durable: bool
) -> float | None:
    """Do not dispatch Max reasoning when its bounded allowance cannot fit.

    This is an admission policy, not a prediction that a model will finish in a
    particular time. Skipping leaves the original collection plan in effect.
    Legacy synchronous callbacks retain their existing twenty-second ceiling.
    """
    if not isfinite(remaining) or remaining <= 0:
        return None
    if durable and effort == ReasoningEffort.MAX and remaining < DURABLE_PLANNING_SECONDS:
        return None
    return min(DURABLE_PLANNING_SECONDS if durable else 20.0, remaining)
