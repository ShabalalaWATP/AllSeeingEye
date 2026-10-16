"""Operational retention defaults, not statutory deadlines or authentication lifetimes."""

from dataclasses import dataclass
from datetime import timedelta

LINK_RETENTION = timedelta(days=7)
# At least the maximum configured refresh lifetime (90 days), plus one day.
FAMILY_RETENTION = timedelta(days=91)


@dataclass(frozen=True, slots=True)
class AuthRetentionPolicy:
    decision_days: int = 90
    batch_size: int = 100
    paused: bool = False

    def __post_init__(self) -> None:
        if not 30 <= self.decision_days <= 3650:
            raise ValueError("Decision retention must be between 30 and 3650 days")
        if not 1 <= self.batch_size <= 100:
            raise ValueError("Retention batches must contain between 1 and 100 rows")
