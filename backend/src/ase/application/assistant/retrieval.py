"""Cooperative retained-source selection with category and publisher diversity."""

import re
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from ase.application.assistant.catalogues import (
    cached_cameras,
    doctrine_sources,
    infrastructure_sources,
)
from ase.application.assistant.intent import TOPICS, QuestionIntent, interpret_question
from ase.application.assistant.sources import event_source, relevance, source_text_size
from ase.application.cameras import CameraCatalogueService
from ase.application.ports.cooperative_feeds import CooperativeEventReader
from ase.application.ports.feeds import EventQuery, EventStore
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.assistant import (
    AssistantContext,
    AssistantInterpretation,
    AssistantQuestion,
    AssistantSource,
    AssistantTimeRange,
)
from ase.domain.events import Category, Event
from ase.domain.grading import SourceProfile
from ase.domain.traffic_classification import is_reported_military
from ase.domain.users import User

PER_CATEGORY = 90
MAX_SCAN_PER_CATEGORY = 900
MAX_SOURCES = 30
MAX_CONTEXT_CHARS = 32_000
MAX_PROVIDER_SOURCES = 6


class AssistantRetrieval:
    def __init__(
        self,
        store: EventStore,
        admission: SourceAdmission,
        cameras: CameraCatalogueService,
        infrastructure: Callable[[], Mapping[str, Any]],
        profiles: Mapping[str, SourceProfile],
    ) -> None:
        self.store, self.admission, self.cameras = store, admission, cameras
        self.infrastructure, self.profiles = infrastructure, profiles

    async def collect(
        self, actor: User, question: AssistantQuestion, *, as_of: datetime | None = None
    ) -> AssistantContext:
        rows: list[tuple[str, AssistantSource]] = []
        capped = False
        count = 0
        intent = interpret_question(question.question, now=as_of or datetime.now(UTC))
        terms = intent.terms
        period = question.time_range or intent.time_range
        requested_categories = {TOPICS[topic] for topic in intent.topics}
        effective_categories = question.source_categories or (
            *(category.value for category in Category),
            "camera",
            "infrastructure",
            "doctrine",
        )
        interpretation = AssistantInterpretation(
            intent.topics,
            intent.countries,
            period.since if period else None,
            period.until if period else None,
            notes=(
                "Today and yesterday use Europe/London calendar days."
                if intent.time_range
                and (
                    "today" in question.question.casefold()
                    or "yesterday" in question.question.casefold()
                )
                else "",
                "Explicit time selection overrides the question's relative wording."
                if question.time_range and intent.time_range
                else "",
            ),
            source_categories=effective_categories,
        )
        interpretation = replace(
            interpretation, notes=tuple(note for note in interpretation.notes if note)
        )
        if intent.clarification and question.selected is None:
            return AssistantContext(
                (),
                0,
                0,
                False,
                ("No sources searched because the requested selection needs clarification.",),
                clarification=intent.clarification,
                interpretation=interpretation,
            )
        if (
            question.scope == "global"
            and question.prior_questions
            and not intent.countries
            and re.search(r"\b(that|those|them)\b", question.question, re.I)
        ):
            return AssistantContext(
                (),
                0,
                0,
                False,
                ("No sources searched while the referenced item or area is ambiguous.",),
                clarification="Select the map item or viewport you mean, or name the place again. "
                "Earlier questions do not identify which previous answer's observations you mean.",
                interpretation=interpretation,
            )
        if question.selected is None or question.selected.kind == "event":
            for category in Category:
                if category.value not in effective_categories:
                    continue
                if requested_categories and category.value not in requested_categories:
                    continue
                if question.selected is not None:
                    event = self.store.get(question.selected.id)
                    events = [event] if event is not None and event.category is category else []
                    if period:
                        events = [row for row in events if _within_period(row.published_at, period)]
                    count += len(events)
                else:
                    events, category_capped, scanned = await self._matching_events(
                        category, question, intent, period
                    )
                    capped = capped or category_capped
                    count += scanned
                rows.extend(
                    (category.value, source)
                    for event in events
                    if question.selected is not None
                    or intent.event_query_military(category) is None
                    or is_reported_military(event)
                    if question.selected is not None
                    or "military" not in terms
                    or event.category is not Category.SPACE
                    or event.attributes.get("military_public_catalogue") is True
                    if (source := event_source(event)) is not None
                )
        cameras, camera_cap, camera_notes = (
            cached_cameras(self.cameras, actor, question)
            if "camera" in effective_categories
            and (not requested_categories or "camera" in requested_categories)
            else ([], False, ())
        )
        infrastructure, infra_cap, infra_notes = (
            infrastructure_sources(self.infrastructure(), question)
            if "infrastructure" in effective_categories
            and (not requested_categories or "infrastructure" in requested_categories)
            else ([], False, ())
        )
        if period:
            cameras = [row for row in cameras if _within_period(row.published_at, period)]
            infrastructure = [
                row for row in infrastructure if _within_period(row.published_at, period)
            ]
        doctrine = (
            doctrine_sources(question, intent)
            if "doctrine" in effective_categories
            and (not requested_categories or "doctrine" in requested_categories)
            else []
        )
        count += len(cameras) + len(infrastructure) + len(doctrine)
        rows.extend(("camera", source) for source in cameras)
        rows.extend(("infrastructure", source) for source in infrastructure)
        rows.extend(("doctrine", source) for source in doctrine)
        enabled = await self.admission.enabled_many(
            tuple(dict.fromkeys(row.source_id for _, row in rows))
        )
        rows = [(category, row) for category, row in rows if enabled.get(row.source_id, False)]
        matched = [
            (category, row)
            for category, row in rows
            if question.selected is not None or intent.accepts(category, row)
        ]
        selected = self._choose(matched, terms)
        notes = (
            "Bounded retained map sample, not an exhaustive search or a provider refresh.",
            "Publication, capture and retrieval times do not necessarily establish event time.",
            "Missing records do not establish absence or source independence.",
            "Text matches and place mentions do not establish incident locations.",
            "GNSS aggregates, Cloudflare Radar aggregates, archived reports and fresh "
            "web research were not searched.",
            "Time selection uses publication timestamps. Undated cameras and "
            "infrastructure are omitted when a time range is set."
            if period
            else "No time bound was applied.",
            *camera_notes,
            *infra_notes,
        )
        return AssistantContext(
            tuple(replace(row, id=f"E{index + 1}") for index, row in enumerate(selected)),
            count,
            len({row.source_id for row in selected}),
            capped or camera_cap or infra_cap or len(selected) < len(matched),
            notes,
            matched_count=len(matched),
            interpretation=interpretation,
        )

    async def _matching_events(
        self,
        category: Category,
        question: AssistantQuestion,
        intent: QuestionIntent,
        period: AssistantTimeRange | None,
    ) -> tuple[list[Event], bool, int]:
        """Filter the date in the store, then scan bounded pages before source selection."""
        matched: list[Event] = []
        offset = 0
        scanned = 0
        while scanned < MAX_SCAN_PER_CATEGORY and len(matched) < PER_CATEGORY:
            query = EventQuery(
                categories=frozenset({category}),
                bbox=question.bbox,
                since=period.since if period else None,
                until=period.until if period else None,
                limit=PER_CATEGORY,
                offset=offset,
                include_unknown_dates=period is None,
                military=intent.event_query_military(category),
            )
            batch = (
                await self.store.read_cooperatively(query, lambda values: values)
                if isinstance(self.store, CooperativeEventReader)
                else self.store.query(query)
            )
            scanned += len(batch)
            offset += len(batch)
            for event in batch:
                source = event_source(event)
                if source and intent.accepts(category.value, source):
                    matched.append(event)
                    if len(matched) >= PER_CATEGORY:
                        break
            if len(batch) < PER_CATEGORY:
                return matched, False, scanned
        return matched, scanned >= MAX_SCAN_PER_CATEGORY or len(matched) >= PER_CATEGORY, scanned

    def _choose(
        self,
        rows: list[tuple[str, AssistantSource]],
        terms: tuple[str, ...],
    ) -> list[AssistantSource]:
        groups: dict[str, list[AssistantSource]] = defaultdict(list)
        for category, row in rows:
            groups[category].append(row)
        for group in groups.values():
            # Stable ties retain the event store's newest-first ordering.
            group.sort(key=lambda row: -relevance(row, terms))
        chosen: list[AssistantSource] = []
        provider_counts: dict[str, int] = defaultdict(int)
        identities: set[tuple[str, str]] = set()
        titles: set[str] = set()
        size = 0
        # Each relevant category gets a turn; within each, prefer the least-used publisher.
        while groups and len(chosen) < MAX_SOURCES:
            active = {}
            for category, group in groups.items():
                group.sort(
                    key=lambda row: (provider_counts[self._provider(row)], -relevance(row, terms))
                )
                while group:
                    row = group.pop(0)
                    key = (row.kind, row.record_id)
                    title = row.title.casefold().strip()
                    cost = source_text_size(row)
                    if (
                        key in identities
                        or title in titles
                        or provider_counts[self._provider(row)] >= MAX_PROVIDER_SOURCES
                        or size + cost > MAX_CONTEXT_CHARS
                    ):
                        continue
                    chosen.append(row)
                    identities.add(key)
                    titles.add(title)
                    size += cost
                    provider_counts[self._provider(row)] += 1
                    break
                if group:
                    active[category] = group
                if len(chosen) >= MAX_SOURCES:
                    break
            groups = active
        return chosen

    def _provider(self, source: AssistantSource) -> str:
        profile = self.profiles.get(source.source_id)
        return (
            profile.independence_key if profile and profile.independence_key else source.source_id
        )


def _within_period(value: datetime | None, period: AssistantTimeRange) -> bool:
    return value is not None and period.since <= value < period.until
