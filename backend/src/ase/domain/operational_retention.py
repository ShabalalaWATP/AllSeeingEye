"""Purpose-based operational windows and conservative category holds."""

from dataclasses import dataclass

CATEGORIES = frozenset({"audit", "llm_usage", "subscription_email", "digest"})
TERMINAL_EMAIL_STATES = ("sent", "failed", "cancelled", "uncertain")


@dataclass(frozen=True, slots=True)
class OperationalRetentionPolicy:
    audit_days: int = 365
    usage_days: int = 400
    delivery_days: int = 90
    batch_size: int = 100
    paused: bool = False
    held_categories: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if any(
            not 30 <= days <= 3650
            for days in (self.audit_days, self.usage_days, self.delivery_days)
        ):
            raise ValueError("Operational retention must be between 30 and 3650 days")
        if not 1 <= self.batch_size <= 100:
            raise ValueError("Retention batches must contain between 1 and 100 rows")
        if not self.held_categories <= CATEGORIES:
            raise ValueError("Unknown operational retention hold category")
