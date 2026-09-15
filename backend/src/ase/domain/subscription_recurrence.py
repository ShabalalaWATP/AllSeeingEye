"""Local calendar slots and half-open observation windows for subscriptions."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ase.domain.report_jobs import job_timestamp
from ase.domain.subscription_editions import ObservationInterval

MONTH_STEPS = {"monthly": 1, "quarterly": 3, "semiannual": 6, "annual": 12}
CADENCES = frozenset({"daily", "weekdays", "weekly", *MONTH_STEPS})
MAX_PREVIEW_SLOTS = 12
MAX_LOOKBACK = timedelta(days=730)
MAX_OVERLAP = timedelta(hours=6)


class WindowPolicy(StrEnum):
    ROLLING_SNAPSHOT = "rolling_snapshot"
    SINCE_LAST_SUCCESS = "since_last_success"


@dataclass(frozen=True, slots=True)
class LocalOccurrence:
    scheduled_date: date
    local: datetime
    utc: datetime
    dst_resolution: str  # normal, gap, or fold

    def __post_init__(self) -> None:
        job_timestamp(self.local)
        job_timestamp(self.utc)
        if self.utc.tzinfo != UTC or self.local.astimezone(UTC) != self.utc:
            raise ValueError("Local and UTC subscription preview times must agree.")
        if self.dst_resolution not in {"normal", "gap", "fold"}:
            raise ValueError("Unknown daylight-saving resolution.")


def _valid_local(wall: datetime, zone: ZoneInfo) -> tuple[datetime, ...]:
    """Round-trip both folds to distinguish valid, repeated and missing wall times."""
    valid: list[datetime] = []
    for fold in (0, 1):
        candidate = wall.replace(tzinfo=zone, fold=fold)
        utc = candidate.astimezone(UTC)
        if utc.astimezone(zone).replace(tzinfo=None) == wall and all(
            prior.astimezone(UTC) != utc for prior in valid
        ):
            valid.append(candidate)
    return tuple(sorted(valid, key=lambda item: item.astimezone(UTC)))


def _resolve_local(wall: datetime, zone: ZoneInfo) -> tuple[datetime, str]:
    valid = _valid_local(wall, zone)
    if valid:
        return valid[0], "fold" if len(valid) == 2 else "normal"
    # Search the minute grid because a 01:30 gap must resolve to 02:00,
    # not 02:30. Forty-eight hours also covers an entire skipped civil day.
    for minutes in range(1, 48 * 60 + 1):
        shifted = wall + timedelta(minutes=minutes)
        valid = _valid_local(shifted, zone)
        if valid:
            return valid[0], "gap"
    raise ValueError("No valid local time follows the subscription's calendar slot.")


@dataclass(frozen=True, slots=True)
class LocalRecurrence:
    timezone: str
    hour: int
    minute: int
    cadence: str
    weekday: int = 0
    monthday: int = 1
    anchor_month: int = 1

    def __post_init__(self) -> None:
        if type(self.timezone) is not str or not 1 <= len(self.timezone) <= 100:
            raise ValueError("Choose a valid IANA timezone.")
        try:
            ZoneInfo(self.timezone)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("Choose a valid IANA timezone.") from exc
        if (
            type(self.hour) is not int
            or not 0 <= self.hour <= 23
            or type(self.minute) is not int
            or not 0 <= self.minute <= 59
            or self.cadence not in CADENCES
            or type(self.weekday) is not int
            or not 0 <= self.weekday <= 6
            or type(self.monthday) is not int
            or not 1 <= self.monthday <= 31
            or type(self.anchor_month) is not int
            or not 1 <= self.anchor_month <= 12
        ):
            raise ValueError("Invalid local subscription recurrence.")

    def _matches(self, day: date) -> bool:
        if self.cadence == "daily":
            return True
        if self.cadence == "weekdays":
            return day.weekday() < 5
        if self.cadence == "weekly":
            return day.weekday() == self.weekday
        months = MONTH_STEPS[self.cadence]
        month_index = day.year * 12 + day.month - 1
        return (month_index - (self.anchor_month - 1)) % months == 0 and day.day == min(
            self.monthday, monthrange(day.year, day.month)[1]
        )

    def preview(self, after_utc: datetime, count: int = 3) -> tuple[LocalOccurrence, ...]:
        """The next distinct due instants strictly after an aware reference time."""
        job_timestamp(after_utc)
        if type(count) is not int or not 1 <= count <= MAX_PREVIEW_SLOTS:
            raise ValueError("Choose between one and twelve preview slots.")
        zone = ZoneInfo(self.timezone)
        after = after_utc.astimezone(UTC)
        start = after.astimezone(zone).date()
        result: list[LocalOccurrence] = []
        seen: set[datetime] = set()
        for days in range(366 * (count + 2) + 32):
            scheduled = start + timedelta(days=days)
            if not self._matches(scheduled):
                continue
            wall = datetime.combine(scheduled, time(self.hour, self.minute))
            local, resolution = _resolve_local(wall, zone)
            due = local.astimezone(UTC)
            if due > after and due not in seen:
                result.append(LocalOccurrence(scheduled, local, due, resolution))
                seen.add(due)
                if len(result) == count:
                    return tuple(result)
        raise ValueError("The recurrence has no upcoming slots in its preview horizon.")

    def next_three(self, after_utc: datetime) -> tuple[LocalOccurrence, ...]:
        return self.preview(after_utc, 3)


@dataclass(frozen=True, slots=True)
class RequestedWindow:
    interval: ObservationInterval | None
    overlap: timedelta
    covered_by_newer: bool

    def __post_init__(self) -> None:
        if self.overlap < timedelta() or self.overlap > MAX_OVERLAP:
            raise ValueError("Subscription overlap exceeds its bound.")
        if (self.interval is None) != self.covered_by_newer:
            raise ValueError("Only a covered old slot can omit its observation interval.")


def requested_window(
    policy: WindowPolicy,
    due_at_utc: datetime,
    baseline_lookback: timedelta,
    *,
    compatible_complete_cutoff: datetime | None = None,
) -> RequestedWindow:
    """Plan the immutable requested interval from covered, compatible dates only.

    An accepted analytical baseline does not alter `compatible_complete_cutoff`.
    Callers mark a covered old slot skipped and link its newer covering edition.
    """
    if not isinstance(policy, WindowPolicy):
        raise ValueError("Choose a supported collection window policy.")
    job_timestamp(due_at_utc)
    if not timedelta(hours=1) <= baseline_lookback <= MAX_LOOKBACK:
        raise ValueError("The baseline lookback must be between one hour and 730 days.")
    due = due_at_utc.astimezone(UTC)
    cutoff = None
    if compatible_complete_cutoff is not None:
        job_timestamp(compatible_complete_cutoff)
        cutoff = compatible_complete_cutoff.astimezone(UTC)
        if cutoff >= due:
            return RequestedWindow(None, timedelta(), True)
    if policy is WindowPolicy.ROLLING_SNAPSHOT or cutoff is None:
        overlap = min(MAX_OVERLAP, baseline_lookback / 4)
        return RequestedWindow(ObservationInterval(due - baseline_lookback, due), overlap, False)
    positive_span = due - cutoff
    overlap = min(MAX_OVERLAP, positive_span / 4)
    return RequestedWindow(ObservationInterval(cutoff - overlap, due), overlap, False)
