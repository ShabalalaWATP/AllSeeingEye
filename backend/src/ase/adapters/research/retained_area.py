"""Area-only access to the bounded shared public store, never a fresh provider search."""

from collections import Counter
from functools import partial

from ase.adapters.research.retained_area_selection import (
    SCAN_PER_CATEGORY,
    AreaPointFilter,
    AreaSnapshot,
    enabled_event,
    fair_selection,
    select_snapshot,
)
from ase.application.feeds.cooperative_work import joined_thread_call
from ase.application.ports.cooperative_feeds import CooperativeEventReader
from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.events import Category, Event
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.research import (
    CollectionAttempt,
    CollectionStatus,
    ResearchBatch,
    ResearchFocus,
    ResearchMode,
    ResearchQuery,
)

SOURCE_ID = "research-retained-area-feeds"
LIMITATIONS = (
    "Retained public feeds only, not a fresh external search or complete history. "
    "Positions are timestamped snapshots, not guaranteed current locations or "
    "satellite visibility. "
    "Unknown dates, imprecise/ungeolocated points and observation footprints are excluded. "
    "CCTV imagery and infrastructure catalogues are not searched. "
    "Empty or missing categories do not establish absence of activity."
)


class RetainedAreaFeedProvider:
    id = SOURCE_ID
    name = "Retained public feeds"
    temporal_scope = (
        "Acquisition/publication interval within the currently retained feed cache. "
        "No historical backfill or refresh; feed outages, retention and stale positions "
        "limit coverage."
    )
    spatial_scope = (
        "Exact polygon or split multipolygon filtering of enabled retained precise point feeds: "
        "conflicts, news, hazards, flights, vessels, satellites and other point records. "
        "Up to 2,000 candidates per category; fair source/category sampling retains at most "
        "88 quick or 264 detailed records. Question/language terms do not filter "
        "these area records. " + LIMITATIONS
    )

    def __init__(
        self,
        store: EventStore,
        *,
        admission: SourceAdmission | None = None,
        disabled: tuple[str, ...] = (),
    ) -> None:
        self._store, self._admission = store, admission
        self._disabled = frozenset(disabled)

    def supports(self, query: ResearchQuery) -> bool:
        return (
            query.area is not None
            and query.focus is ResearchFocus.GENERAL
            and query.effective_time_basis is EvidenceTimeBasis.RESEARCH
        )

    def supports_area(self, query: ResearchQuery) -> bool:
        return self.supports(query)

    def _receipt(
        self, status: CollectionStatus, explanation: str, items: tuple[Event, ...] = ()
    ) -> ResearchBatch:
        return ResearchBatch(
            items,
            (CollectionAttempt(self.id, self.name, status, len(items), explanation[:1000]),),
        )

    def _disabled_result(self) -> ResearchBatch:
        return self._receipt(
            CollectionStatus.UNAVAILABLE,
            "Retained area feeds are disabled by the administrator. No results were admitted.",
        )

    async def collect(self, query: ResearchQuery) -> ResearchBatch:
        if not self.supports(query) or query.area is None:
            return self._receipt(CollectionStatus.UNSUPPORTED, self.spatial_scope)
        area = query.area
        if self.id in self._disabled or (
            self._admission is not None and not await self._admission.enabled(self.id)
        ):
            return self._disabled_result()
        try:
            spatial = await joined_thread_call(lambda: AreaPointFilter(area))
        except ValueError:
            return self._receipt(
                CollectionStatus.UNSUPPORTED,
                "The supplied polygon topology is unsupported. No envelope search was substituted.",
            )
        snapshots = []
        for category in Category:
            request = EventQuery(
                categories=frozenset({category}),
                bbox=spatial.bounds,
                country_iso=query.country_iso,
                since=query.since,
                until=query.until,
                time_basis=query.effective_time_basis,
                limit=SCAN_PER_CATEGORY + 1,
            )

            def project(events: list[Event]) -> AreaSnapshot:
                return select_snapshot(events, spatial, query)

            if isinstance(self._store, CooperativeEventReader):
                snapshot = await self._store.read_cooperatively(request, project)
            else:
                # Production uses the cooperative shared store. Small port fakes
                # still run expensive geometry projection outside the event loop.
                events = self._store.query(request)
                snapshot = await joined_thread_call(partial(project, events))
            snapshots.append(snapshot)
        candidates = tuple(event for snapshot in snapshots for event in snapshot.items)
        source_ids = tuple(sorted({event.source_id for event in candidates}))
        if self._admission is None:
            return self._result(query, snapshots, candidates, dict.fromkeys(source_ids, True))
        # One final release guard covers both this capability and every underlying
        # source. Composition must not wrap this provider in a second release guard.
        async with self._admission.guard():
            if not await self._admission.enabled(self.id):
                return self._disabled_result()
            enabled = await self._admission.enabled_many(source_ids)
            return self._result(query, snapshots, candidates, enabled)

    def _result(
        self,
        query: ResearchQuery,
        snapshots: list[AreaSnapshot],
        candidates: tuple[Event, ...],
        enabled: dict[str, bool],
    ) -> ResearchBatch:
        admitted = tuple(
            event for event in candidates if enabled_event(event, self._disabled, enabled)
        )
        items = fair_selection(admitted, 8 if query.mode is ResearchMode.QUICK else 24)
        counts = Counter(event.category.value for event in items)
        sources = {event.source_id for event in items}
        excluded = sum(snapshot.excluded for snapshot in snapshots)
        truncated = any(snapshot.truncated for snapshot in snapshots) or len(admitted) > len(items)
        detail = (
            f"{len(items)} records from {len(sources)} original sources. Categories: "
            + (", ".join(f"{key} {value}" for key, value in sorted(counts.items())) or "none")
            + f". {excluded} scanned candidates excluded by exact location/scope checks; "
            + f"{len(candidates) - len(admitted)} disabled-source records excluded. "
            + ("Bounded selection is truncated. " if truncated else "")
            + "No admitted records: "
            + (
                ", ".join(category.value for category in Category if category.value not in counts)
                or "none"
            )
            + "."
        )
        return self._receipt(
            CollectionStatus.COMPLETED if items else CollectionStatus.EMPTY,
            LIMITATIONS + " " + detail,
            items,
        )
