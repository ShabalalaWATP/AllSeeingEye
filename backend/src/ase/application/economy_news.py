"""Bounded current economic headlines from reviewed topic-specific publishers."""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from urllib.parse import urlsplit

from ase.application.ports import Clock
from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.economy_news import (
    ECONOMIC_NEWS_IDS,
    EconomyRegion,
    PublisherViewpoint,
    economic_regions,
    economic_viewpoint,
)
from ase.domain.economy_periods import EconomyWindowDays, economy_window
from ase.domain.events import Category
from ase.domain.sources import SourceSpec

WINDOW_HOURS = 48
_COVERAGE_DETAIL = (
    "Available publisher headlines, refreshed by enabled feed collectors. "
    "Publisher feeds and the bounded local cache may not retain the entire selected period. "
    "Region labels use an explicit headline mention or the feed's topic remit, not event "
    "locations. Official and state-aligned sources represent their issuers' perspectives. "
    "Missing coverage is not evidence that no developments occurred."
)


def coverage_note(days: EconomyWindowDays) -> str:
    return f"Economic news published in the selected {int(days)} days. {_COVERAGE_DETAIL}"


COVERAGE_NOTE = coverage_note(EconomyWindowDays.TWO)


@dataclass(frozen=True, slots=True)
class EconomyNewsItem:
    id: str
    title: str
    url: str
    source_id: str
    source_name: str
    organisation: str
    published_at: datetime
    region_codes: tuple[str, ...]
    viewpoint: PublisherViewpoint


@dataclass(frozen=True, slots=True)
class EconomyNews:
    items: tuple[EconomyNewsItem, ...]
    as_of: datetime
    window_hours: int = WINDOW_HOURS
    coverage_note: str = COVERAGE_NOTE


class EconomyNewsService:
    def __init__(
        self,
        store: EventStore,
        clock: Clock,
        sources: Mapping[str, SourceSpec],
        admission: SourceAdmission,
    ) -> None:
        self._store, self._clock = store, clock
        self._sources, self._admission = sources, admission

    async def read(
        self,
        region: EconomyRegion = "WORLD",
        limit: int = 60,
        days: EconomyWindowDays = EconomyWindowDays.TWO,
    ) -> EconomyNews:
        days = economy_window(days)
        if region not in {"WORLD", "GB", "US", "RU", "CN", "IR"} or not 1 <= limit <= 100:
            raise ValueError("Unsupported economic news scope")
        enabled = await self._admission.enabled_many(ECONOMIC_NEWS_IDS)
        selected = frozenset(key for key in ECONOMIC_NEWS_IDS if enabled.get(key, False))
        now = self._clock.now()
        result_view = EconomyNews((), now, int(days) * 24, coverage_note(days))
        if not selected:
            return result_view
        since = now - timedelta(days=days)
        events = self._store.query(
            EventQuery(
                categories=frozenset({Category.ECONOMIC}),
                source_ids=selected,
                since=since,
                until=now,
                limit=1000,
            )
        )
        result: list[EconomyNewsItem] = []
        seen: set[str] = set()
        for event in events:
            spec = self._sources.get(event.source_id)
            if (
                spec is None
                or event.published_at is None
                or not since <= event.published_at < now
                or not _safe_link(event.url)
            ):
                continue
            regions = economic_regions(event)
            if region != "WORLD" and region not in regions:
                continue
            fingerprint = " ".join((event.title_en or event.title).casefold().split())
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            result.append(
                EconomyNewsItem(
                    event.id,
                    (event.title_en or event.title)[:300],
                    event.url or "",
                    event.source_id,
                    spec.name,
                    spec.organisation,
                    event.published_at,
                    regions,
                    economic_viewpoint(event),
                )
            )
            if len(result) >= limit:
                break
        # A source disabled while this request was preparing must not be released.
        return await self.refilter(replace(result_view, items=tuple(result)))

    async def refilter(self, result: EconomyNews) -> EconomyNews:
        """Final release under the caller's source guard; no network or store query."""
        enabled = await self._admission.enabled_many(tuple(row.source_id for row in result.items))
        return replace(
            result, items=tuple(row for row in result.items if enabled.get(row.source_id, False))
        )


def _safe_link(value: str | None) -> bool:
    if not value or len(value) > 2048:
        return False
    try:
        url = urlsplit(value)
        return bool(
            url.scheme in {"https", "http"}
            and url.hostname
            and url.username is None
            and url.password is None
        )
    except ValueError:
        return False
