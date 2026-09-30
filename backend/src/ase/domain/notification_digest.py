"""Calendar-day digest windows reuse the subscription daylight-saving policy."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from ase.domain.subscription_recurrence import LocalOccurrence, LocalRecurrence


@dataclass(frozen=True, slots=True)
class DigestPreferences:
    enabled: bool = False
    timezone: str = "UTC"
    hour: int = 8

    def __post_init__(self) -> None:
        LocalRecurrence(self.timezone, self.hour, 0, "daily")


@dataclass(frozen=True, slots=True)
class DigestCounts:
    alerts: int
    finished: int
    failed: int
    reviews: int
    reviews_truncated: bool = False

    @property
    def empty(self) -> bool:
        return not (
            self.alerts or self.finished or self.failed or self.reviews or self.reviews_truncated
        )


def next_digest_at(after: datetime, preferences: DigestPreferences) -> datetime:
    return (
        LocalRecurrence(preferences.timezone, preferences.hour, 0, "daily").preview(after, 1)[0].utc
    )


def latest_digest_slot(now: datetime, preferences: DigestPreferences) -> LocalOccurrence:
    # Four calendar slots cover DST changes and a skipped civil day. An outage
    # produces one current digest covering the whole saved window, not backfill mail.
    slots = LocalRecurrence(preferences.timezone, preferences.hour, 0, "daily").preview(
        now - timedelta(days=3),
        4,
    )
    return max((slot for slot in slots if slot.utc <= now), key=lambda slot: slot.utc)
