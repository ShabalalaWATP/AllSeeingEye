"""Rule-specific sampled hourly means, with explicit warm-up and zero-mean refusal."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from ase.domain.warning import Indicator

WARMUP_HOURS = 7 * 24


@dataclass(frozen=True, slots=True)
class IndicatorBaseline:
    sample_hours: int
    mean: float | None
    earliest: datetime | None
    as_of: datetime

    @property
    def ready(self) -> bool:
        return (
            self.sample_hours >= WARMUP_HOURS
            and self.earliest is not None
            and self.earliest <= self.as_of - timedelta(days=7)
            and self.mean is not None
            and self.mean > 0
        )

    @property
    def reason(self) -> str:
        if (
            self.sample_hours < WARMUP_HOURS
            or self.earliest is None
            or (self.earliest > self.as_of - timedelta(days=7))
        ):
            return "Warming up: at least seven days and 168 sampled hours are required."
        if not self.mean:
            return "A ratio is unavailable while the sampled mean is zero."
        return "Ready; mean is based on sampled hours, excluding the current hour."


def matching_semantics(rule: Indicator) -> tuple[object, ...]:
    """Changes in matching, enabled state or mode start a fresh sampling cohort."""
    return (
        rule.countries,
        rule.bbox,
        rule.research_area,
        rule.categories,
        rule.keywords,
        rule.severity_floor,
        rule.enabled,
        rule.baseline_ratio is not None,
    )
