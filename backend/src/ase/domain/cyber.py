"""Cyber reporting periods and explicit observation types, without attack attribution."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import IntEnum, StrEnum

from ase.domain.cyber_actors import CyberActorMention

CYBER_PUBLISHER_IDS = (
    "cyber_ncsc_reports",
    "cyber_ncsc_news",
    "cyber_microsoft_threat_intelligence",
    "cyber_cisco_talos",
    "cyber_google_threat_intelligence",
    "cyber_cert_eu",
    "cyber_acsc_advisories",
)
CYBER_TELEMETRY_IDS = ("cisa_kev", "ransomware_live", "ioda_outages")
ACTOR_REFERENCE_SOURCE_ID = "mitre_attack"


class CyberWindowDays(IntEnum):
    TWO = 2
    FIVE = 5
    SEVEN = 7
    FOURTEEN = 14


def cyber_window(value: int) -> CyberWindowDays:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("Choose a 2, 5, 7 or 14 day cyber briefing")
    return CyberWindowDays(value)


class CyberKind(StrEnum):
    RANSOMWARE_CLAIM = "ransomware_claim"
    OUTAGE_SIGNAL = "outage_signal"
    KNOWN_EXPLOITED_VULNERABILITY = "known_exploited_vulnerability"
    ADVISORY = "advisory"
    THREAT_REPORT = "threat_report"
    OTHER = "other"


def cyber_kind(subtype: str) -> CyberKind:
    if subtype == "ransomware":
        return CyberKind.RANSOMWARE_CLAIM
    if subtype == "outage":
        return CyberKind.OUTAGE_SIGNAL
    try:
        return CyberKind(subtype)
    except ValueError:
        return CyberKind.OTHER


@dataclass(frozen=True, slots=True)
class CyberKev:
    cve: str
    vendor: str
    product: str
    date_added: date
    due_date: str
    ransomware_use: str
    cwes: str
    required_action: str


@dataclass(frozen=True, slots=True)
class CyberItem:
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
    actor_mentions: tuple[CyberActorMention, ...]
    kev: CyberKev | None


@dataclass(frozen=True, slots=True)
class CyberKindCount:
    kind: CyberKind
    count: int


@dataclass(frozen=True, slots=True)
class CyberDailyCount:
    day: date
    total: int
    counts: tuple[CyberKindCount, ...]


@dataclass(frozen=True, slots=True)
class CyberTally:
    key: str
    count: int


@dataclass(frozen=True, slots=True)
class CyberActorTally:
    group_id: str
    name: str
    count: int


@dataclass(frozen=True, slots=True)
class CyberSource:
    source_id: str
    name: str
    organisation: str
    url: str
    status: str
    last_success: datetime | None
    last_error_at: datetime | None
    retained_count: int


@dataclass(frozen=True, slots=True)
class CyberSnapshot:
    as_of: datetime
    window_days: CyberWindowDays
    period_from: datetime
    period_to: datetime
    coverage_note: str
    retained_count: int
    returned_count: int
    truncated: bool
    counts: tuple[CyberKindCount, ...]
    timeline: tuple[CyberDailyCount, ...]
    top_countries: tuple[CyberTally, ...]
    actor_mentions: tuple[CyberActorTally, ...]
    sources: tuple[CyberSource, ...]
    items: tuple[CyberItem, ...]
