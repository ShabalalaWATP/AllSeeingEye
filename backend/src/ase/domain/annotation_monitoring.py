"""Durable selected-root observation, separate from successful research baselines."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from ase.domain.annotation_comparison import AnnotationKind
from ase.domain.errors import Conflict, InvalidRequest

MonitorMode = Literal["selected_roots", "report_inventory"]
MAX_MONITOR_PENDING_EVENTS = 2000

MonitorStatus = Literal["active", "paused", "unavailable"]
MonitorAction = Literal["configure", "pause", "resume_catch_up", "resume_rebaseline"]
MAX_MONITORS_PER_SCOPE = 20
MAX_MONITORS_GLOBAL = 1000
MAX_MONITOR_GLOBAL_BYTES = 256 * 1024 * 1024
MAX_MONITOR_BYTES = 64 * 1024 * 1024
MAX_TRANSITIONS = 2000


@dataclass(frozen=True, slots=True)
class WatchedRevision:
    kind: AnnotationKind
    root_id: UUID
    revision_id: UUID


@dataclass(frozen=True, slots=True)
class AnnotationMonitor:
    id: UUID
    created_by: UUID
    team_id: UUID | None
    report_id: UUID
    version_number: int
    name: str
    categories: tuple[AnnotationKind, ...]
    notify_on_change: bool
    status: MonitorStatus
    unavailable_reason: str | None
    revision: int
    checkpoint_id: UUID
    checkpoint_number: int
    watches: tuple[WatchedRevision, ...]
    created_at: datetime
    updated_at: datetime
    mode: MonitorMode = "selected_roots"


@dataclass(frozen=True, slots=True)
class RevisionObservation:
    id: int
    monitor_id: UUID
    kind: AnnotationKind
    root_id: UUID
    previous_revision_id: UUID | None
    revision_id: UUID
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AnnotationTransition:
    id: UUID
    monitor_id: UUID
    checkpoint_before: UUID
    checkpoint_after: UUID
    sequence: int
    kind: Literal["revision", "rebaseline"]
    recorded_at: datetime
    changed_categories: tuple[AnnotationKind, ...]
    alert_id: UUID | None
    comparison_sha256: str
    configuration_revision: int
    notification_categories: tuple[AnnotationKind, ...]
    notify_on_change: bool


class InventoryCapacityUnavailable(InvalidRequest):
    """A bounded subscription cannot retain the complete inventory."""


class InventoryHistoryGap(Conflict):
    """An inventory root lacks its required retained creation event."""
