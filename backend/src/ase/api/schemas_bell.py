"""JSON contracts for the in-app notification bell."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ase.application.bell.summary import BellSummary
from ase.domain.bell import (
    MAX_ACKNOWLEDGE_BATCH,
    AcknowledgeOutcome,
    AlertDestination,
    BellAlert,
    BellAlertSection,
    BellKind,
    BellPreferences,
    DestinationKind,
)


class BellAlertOut(BaseModel):
    id: UUID
    title: str
    summary: str
    fired_at: datetime
    indicator_id: UUID | None
    report_id: UUID | None
    annotation_monitor_id: UUID | None
    team_id: UUID | None
    team_name: str | None
    # Whether this caller may acknowledge it now; team acknowledgement is shared.
    can_acknowledge: bool

    @classmethod
    def build(cls, item: BellAlert) -> BellAlertOut:
        alert = item.alert
        return cls(
            id=alert.id,
            title=alert.title,
            summary=alert.summary,
            fired_at=alert.fired_at,
            indicator_id=alert.indicator_id,
            report_id=alert.report_id,
            annotation_monitor_id=alert.annotation_monitor_id,
            team_id=alert.team_id,
            team_name=item.team_name,
            can_acknowledge=item.can_acknowledge,
        )


class BellAlertSectionOut(BaseModel):
    items: list[BellAlertOut]
    total: int
    muted: bool

    @classmethod
    def build(cls, section: BellAlertSection) -> BellAlertSectionOut:
        return cls(
            items=[BellAlertOut.build(item) for item in section.items],
            total=section.total,
            muted=section.muted,
        )


class MutedRuleOut(BaseModel):
    indicator_id: UUID
    name: str
    muted_at: datetime


class BellPreferencesOut(BaseModel):
    muted_kinds: list[BellKind]
    muted_rules: list[MutedRuleOut]

    @classmethod
    def build(cls, preferences: BellPreferences) -> BellPreferencesOut:
        return cls(
            muted_kinds=sorted(preferences.muted_kinds),
            muted_rules=[
                MutedRuleOut(indicator_id=rule.indicator_id, name=rule.name, muted_at=rule.muted_at)
                for rule in preferences.muted_rules
            ],
        )


class BellPreferencesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    muted_kinds: list[BellKind] = Field(max_length=len(BellKind) * 2)


class BellOut(BaseModel):
    window_days: int
    alerts: BellAlertSectionOut
    preferences: BellPreferencesOut

    @classmethod
    def build(cls, summary: BellSummary) -> BellOut:
        return cls(
            window_days=summary.window_days,
            alerts=BellAlertSectionOut.build(summary.alerts),
            preferences=BellPreferencesOut.build(summary.preferences),
        )


class AlertDestinationOut(BaseModel):
    kind: DestinationKind
    available: bool
    report_id: UUID | None
    monitor_id: UUID | None
    transition_id: UUID | None
    message: str | None

    @classmethod
    def build(cls, destination: AlertDestination) -> AlertDestinationOut:
        return cls(
            kind=destination.kind,
            available=destination.available,
            report_id=destination.report_id,
            monitor_id=destination.monitor_id,
            transition_id=destination.transition_id,
            message=destination.message,
        )


class BellAcknowledgeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_ids: list[UUID] = Field(min_length=1, max_length=MAX_ACKNOWLEDGE_BATCH)


class AcknowledgeFailureOut(BaseModel):
    alert_id: UUID
    message: str


class BellAcknowledgeOut(BaseModel):
    acknowledged: list[UUID]
    failed: list[AcknowledgeFailureOut]

    @classmethod
    def build(cls, outcome: AcknowledgeOutcome) -> BellAcknowledgeOut:
        return cls(
            acknowledged=list(outcome.acknowledged),
            failed=[
                AcknowledgeFailureOut(alert_id=item.alert_id, message=item.message)
                for item in outcome.failed
            ],
        )
