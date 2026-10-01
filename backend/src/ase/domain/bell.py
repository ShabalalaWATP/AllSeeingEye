"""The in-app notification bell: what one account chooses to see.

A bell preference changes only that viewer's in-app list and badge. It never pauses
rule evaluation, deletes alerts or acknowledges them for anyone. Out-of-app delivery
(email, push, feeds) is a separate opt-in layer and reads none of these choices.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from ase.domain.warning import Alert

# Matches the Alerts page default so both describe the same alerts.
BELL_ALERT_WINDOW = timedelta(days=7)
BELL_SHOWN = 5
MAX_ACKNOWLEDGE_BATCH = 20
MAX_RULE_MUTES = 100
# A content-free bus signal: open streams refetch the bell through authorised reads.
BELL_CHANGED = "bell.changed"


class BellKind(StrEnum):
    """In-app notification kinds a viewer may mute."""

    ALERTS = "alerts"
    RESEARCH = "research"
    MENTIONS = "mentions"


@dataclass(frozen=True, slots=True)
class MutedRule:
    indicator_id: UUID
    name: str
    muted_at: datetime


@dataclass(frozen=True, slots=True)
class BellPreferences:
    user_id: UUID
    muted_kinds: frozenset[BellKind] = frozenset()
    # Only rules the viewer can still read; a hidden rule's name never leaks.
    muted_rules: tuple[MutedRule, ...] = ()

    def shows(self, kind: BellKind) -> bool:
        return kind not in self.muted_kinds


@dataclass(frozen=True, slots=True)
class BellAlert:
    alert: Alert
    can_acknowledge: bool
    team_name: str | None


@dataclass(frozen=True, slots=True)
class BellAlertSection:
    items: tuple[BellAlert, ...]
    total: int
    muted: bool


class DestinationKind(StrEnum):
    REPORT = "report"
    TRANSITION = "transition"
    ALERTS = "alerts"


@dataclass(frozen=True, slots=True)
class AlertDestination:
    """Where a bell alert opens. Identifiers are present only while available."""

    kind: DestinationKind
    available: bool = True
    report_id: UUID | None = None
    monitor_id: UUID | None = None
    transition_id: UUID | None = None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class AcknowledgeFailure:
    alert_id: UUID
    message: str


@dataclass(frozen=True, slots=True)
class AcknowledgeOutcome:
    acknowledged: tuple[UUID, ...]
    failed: tuple[AcknowledgeFailure, ...]
