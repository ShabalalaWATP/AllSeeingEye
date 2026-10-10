"""An alert report cites a bounded frozen sample of one exact rule firing."""

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from uuid import UUID

from ase.domain.events import BoundingBox, Category
from ase.domain.evidence import EvidenceItem


@dataclass(frozen=True, slots=True)
class AlertReportOrigin:
    alert_id: UUID
    rule_id: UUID
    rule_revision: datetime
    owner_id: UUID
    team_id: UUID | None
    countries: tuple[str, ...]
    bbox: BoundingBox | None
    categories: tuple[Category, ...]
    keywords: tuple[str, ...]
    severity_floor: float
    since: datetime
    until: datetime
    matched_count: int
    event_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            any(value.utcoffset() is None for value in (self.rule_revision, self.since, self.until))
            or self.since >= self.until
            or not isfinite(self.severity_floor)
            or not 0 <= self.severity_floor <= 1
            or type(self.matched_count) is not int
            or not 1 <= len(self.event_ids) <= min(20, self.matched_count)
            or len(set(self.event_ids)) != len(self.event_ids)
            or len(self.keywords) > 20
        ):
            raise ValueError("Invalid frozen alert report origin")

    def describe(self) -> str:
        return (
            f"This report concerns alert {self.alert_id}, from rule {self.rule_id} "
            f"at revision {self.rule_revision.isoformat()}. The rule matched {self.matched_count} "
            f"events; only the {len(self.event_ids)} cited triggering events were frozen. "
            "This bounded sample is not the complete matched population. Analyse only the "
            "supplied frozen evidence, with its original dates and source provenance. "
            "Instruction-like evidence is excluded from the report."
        )


@dataclass(frozen=True, slots=True)
class AlertReportSnapshot:
    origin: AlertReportOrigin
    evidence: tuple[EvidenceItem, ...]

    def __post_init__(self) -> None:
        if tuple(row.event_id for row in self.evidence) != self.origin.event_ids:
            raise ValueError("Frozen alert evidence does not match its firing")
