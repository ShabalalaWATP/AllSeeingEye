"""Resolve user ceilings against the authorised model and existing collection tier."""

from dataclasses import dataclass

from ase.application.report_jobs.budget import MAX_CALLS, MAX_OUTPUT_TOKENS
from ase.application.research.budget import CollectionBudget
from ase.domain.research_brief import ResearchBrief
from ase.domain.research_brief_values import BriefValidationError


@dataclass(frozen=True, slots=True)
class BriefAuthorisedCaps:
    """Supplied by admission after the model profile and authority are resolved."""

    max_passes: int
    max_external_operations: int
    max_model_calls: int
    max_output_tokens: int
    max_collection_seconds: int


@dataclass(frozen=True, slots=True)
class ResolvedBriefLimits:
    max_passes: int
    max_external_operations: int
    max_model_calls: int
    max_output_tokens: int
    max_collection_seconds: int
    policy_id: str


def resolve_brief_limits(brief: ResearchBrief, caps: BriefAuthorisedCaps) -> ResolvedBriefLimits:
    """Freeze one run's limits without editing the reusable brief definition."""
    if not isinstance(brief, ResearchBrief) or not isinstance(caps, BriefAuthorisedCaps):
        raise BriefValidationError("limits", "Authorised capacity is required")
    tier = CollectionBudget.for_mode(brief.output.depth)
    allowed = {
        "max_passes": min(2, caps.max_passes),
        "max_external_operations": min(tier.requests, caps.max_external_operations),
        "max_model_calls": min(MAX_CALLS, caps.max_model_calls),
        "max_output_tokens": min(MAX_OUTPUT_TOKENS, caps.max_output_tokens),
        "max_collection_seconds": min(int(tier.seconds), caps.max_collection_seconds),
    }
    if any(type(value) is not int or value < 1 for value in allowed.values()):
        raise BriefValidationError("limits", "Authorised capacity is unavailable")
    effective: dict[str, int] = {}
    for field, maximum in allowed.items():
        requested = getattr(brief.limits, field)
        if requested is not None and requested > maximum:
            raise BriefValidationError(
                f"limits.{field}", "Requested limit exceeds authorised capacity"
            )
        effective[field] = requested if requested is not None else maximum
    return ResolvedBriefLimits(**effective, policy_id=brief.limits.policy_id)
