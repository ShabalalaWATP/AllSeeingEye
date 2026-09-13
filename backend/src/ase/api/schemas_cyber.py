"""Cyber workspace responses with bounded source observations and reference knowledge."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from ase.api.routers.daily_briefing import DailyBriefingOut
from ase.application.feeds.health import SourceStatus
from ase.domain.cyber import CyberKind, CyberWindowDays
from ase.domain.cyber_themes import CyberTheme


class _FromAttributes(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CyberActorMentionOut(_FromAttributes):
    group_id: str
    matched_name: str


class CyberKevOut(_FromAttributes):
    cve: str
    vendor: str
    product: str
    date_added: date
    due_date: str
    ransomware_use: str
    cwes: str
    required_action: str


class CyberItemOut(_FromAttributes):
    id: str
    kind: CyberKind
    title: str
    summary: str | None
    url: str
    source_id: str
    source_name: str
    organisation: str
    published_at: datetime
    observed_at: datetime
    country_iso: str | None
    grade: str
    actor_mentions: list[CyberActorMentionOut]
    kev: CyberKevOut | None
    themes: list[CyberTheme]


class CyberThemeTallyOut(_FromAttributes):
    theme: CyberTheme
    count: int
    daily: list[int]


class CyberStateTallyOut(_FromAttributes):
    state: str
    count: int
    group_ids: list[str]


class CyberKindCountOut(_FromAttributes):
    kind: CyberKind
    count: int


class CyberDailyCountOut(_FromAttributes):
    day: date
    total: int
    counts: list[CyberKindCountOut]


class CyberTallyOut(_FromAttributes):
    key: str
    count: int


class CyberActorTallyOut(_FromAttributes):
    group_id: str
    name: str
    count: int


class CyberSourceOut(_FromAttributes):
    source_id: str
    name: str
    organisation: str
    url: str
    status: SourceStatus
    last_success: datetime | None
    last_error_at: datetime | None
    retained_count: int


class CyberSnapshotOut(_FromAttributes):
    as_of: datetime
    window_days: CyberWindowDays
    period_from: datetime
    period_to: datetime
    coverage_note: str
    retained_count: int
    returned_count: int
    truncated: bool
    counts: list[CyberKindCountOut]
    timeline: list[CyberDailyCountOut]
    top_countries: list[CyberTallyOut]
    actor_mentions: list[CyberActorTallyOut]
    sources: list[CyberSourceOut]
    items: list[CyberItemOut]
    themes: list[CyberThemeTallyOut]
    state_mentions: list[CyberStateTallyOut]


class RadarAttackCountryOut(_FromAttributes):
    country_iso: str
    country_name: str
    rank: int
    share_percent: float


class RadarAttackLayerOut(_FromAttributes):
    layer: Literal["layer3", "layer7"]
    period_from: datetime
    period_to: datetime
    updated_at: datetime | None
    unit: Literal["bytes", "requests"]
    countries: list[RadarAttackCountryOut]


class RadarAttackSnapshotOut(_FromAttributes):
    status: Literal["ready", "partial", "stale", "unavailable", "not_configured", "disabled"]
    fetched_at: datetime | None
    layers: list[RadarAttackLayerOut]
    source_url: str


class CyberActorOut(_FromAttributes):
    group_id: str
    name: str
    associated_names: list[str]
    description: str
    url: str
    modified_at: datetime
    technique_ids: list[str]
    technique_count: int
    state_association: str | None


class CyberActorCatalogueOut(_FromAttributes):
    source_id: str
    version: str
    released_at: datetime
    retrieved_at: datetime
    source_url: str
    source_sha256: str
    licence_url: str
    attribution: str
    limitations: str
    actors: list[CyberActorOut]


class CyberActorsOut(BaseModel):
    available: bool
    catalogue: CyberActorCatalogueOut | None
    coverage_note: str


class CyberBriefingOut(DailyBriefingOut):
    window_days: CyberWindowDays
    period_from: datetime
    period_to: datetime
