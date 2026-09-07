"""Explicit selected-root monitoring requests, scoped state and immutable history."""

from dataclasses import asdict
from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ase.api.schemas_annotation_comparisons import ComparisonSelectionIn
from ase.domain.annotation_comparison import AnnotationComparison, AnnotationKind
from ase.domain.annotation_monitoring import (
    AnnotationMonitor,
    AnnotationTransition,
    MonitorAction,
    MonitorStatus,
)


class AnnotationMonitorCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    selection: ComparisonSelectionIn
    categories: list[AnnotationKind] = Field(min_length=1, max_length=3)
    notify_on_change: bool = False


class AnnotationMonitorUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(strict=True, ge=1)
    action: MonitorAction
    rebaseline: bool = False
    name: str | None = Field(default=None, min_length=1, max_length=120)
    categories: list[AnnotationKind] | None = Field(default=None, min_length=1, max_length=3)
    notify_on_change: bool | None = None

    @model_validator(mode="after")
    def configure_only(self) -> Self:
        if self.action != "configure" and (
            self.rebaseline
            or any(
                value is not None for value in (self.name, self.categories, self.notify_on_change)
            )
        ):
            raise ValueError("Change configuration separately from monitoring state")
        return self


class AnnotationMonitorOut(BaseModel):
    id: UUID
    created_by: UUID
    team_id: UUID | None
    report_id: UUID
    version_number: int
    name: str
    categories: list[AnnotationKind]
    notify_on_change: bool
    status: MonitorStatus
    unavailable_reason: str | None
    revision: int
    checkpoint_id: UUID
    checkpoint_number: int
    selection: ComparisonSelectionIn
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_monitor(cls, value: AnnotationMonitor) -> "AnnotationMonitorOut":
        data = asdict(value)
        data.pop("watches")
        selection: dict[str, object] = {
            "report_id": value.report_id,
            "version_number": value.version_number,
        }
        for kind, key, root_key in (
            ("claim", "revisions", "claim_id"),
            ("identity", "identity_revisions", "decision_id"),
            ("relationship", "relationship_revisions", "relationship_id"),
        ):
            selection[key] = [
                {root_key: w.root_id, "revision_id": w.revision_id}
                for w in value.watches
                if w.kind == kind
            ]
        return cls.model_validate({**data, "selection": selection})


class AnnotationMonitorsOut(BaseModel):
    items: list[AnnotationMonitorOut]
    total: int
    limit: int
    offset: int


class AnnotationTransitionOut(BaseModel):
    id: UUID
    monitor_id: UUID
    checkpoint_before: UUID
    checkpoint_after: UUID
    sequence: int
    kind: Annotated[str, Field(pattern="^(revision|rebaseline)$")]
    recorded_at: datetime
    changed_categories: list[AnnotationKind]
    alert_id: UUID | None
    comparison_sha256: str
    configuration_revision: int
    notification_categories: list[AnnotationKind]
    notify_on_change: bool

    @classmethod
    def from_transition(cls, value: AnnotationTransition) -> "AnnotationTransitionOut":
        return cls.model_validate(asdict(value))


class AnnotationTransitionsOut(BaseModel):
    items: list[AnnotationTransitionOut]
    total: int
    limit: int
    offset: int


class AnnotationTransitionDetailOut(BaseModel):
    transition: AnnotationTransitionOut
    comparison: AnnotationComparison


class AnnotationTransitionExportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_comparison_sha256: str = Field(pattern="^[0-9a-f]{64}$")
