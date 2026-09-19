"""Validate and build the standing definition of a subscription."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ase.application.reports.templates import TEMPLATES
from ase.application.schedules.edition_planning import rebased_next_run
from ase.application.schedules.validation import validate_subscription_scope
from ase.domain.errors import InvalidRequest
from ase.domain.events import Category
from ase.domain.regions import Region, normalise_regions
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_area import ResearchArea
from ase.domain.research_scope import MAX_RESEARCH_HOURS, normalise_countries
from ase.domain.schedules import CADENCES, DEFAULT_CADENCE, Schedule
from ase.domain.subscription_recurrence import LocalRecurrence, WindowPolicy

MAX_THEMES = 4

MAX_WINDOW_HOURS = MAX_RESEARCH_HOURS


@dataclass(frozen=True, slots=True)
class ScheduleInput:
    name: str
    template_id: str
    country_iso: str | None = None
    plan_id: UUID | None = None
    hour_utc: int = 6
    cadence: str = DEFAULT_CADENCE
    weekday: int = 0
    window_hours: int | None = None
    enabled: bool = True
    team_id: UUID | None = None
    notify_on_change: bool = False
    question: str | None = None
    research_mode: ResearchMode | None = None
    research_languages: tuple[str, ...] = ("en",)
    research_focus: ResearchFocus = ResearchFocus.GENERAL
    research_subject: str | None = None
    country_isos: tuple[str, ...] = ()
    # Up to four themes narrow the evidence categories; regions widen the country filter.
    categories: tuple[Category, ...] = ()
    regions: tuple[Region, ...] = ()
    monthday: int = 1
    research_web_search: bool = False
    research_source_ids: tuple[str, ...] | None = None
    anchor_month: int = 1
    conflict_id: str | None = None
    hazard: str | None = None
    research_area: ResearchArea | None = None
    disclose_area_to_provider: bool = False
    avoid_repetition: bool = True
    timezone: str = "UTC"
    local_hour: int | None = None
    local_minute: int = 0
    collection_policy: WindowPolicy = WindowPolicy.ROLLING_SNAPSHOT
    brief_id: UUID | None = None
    brief_revision: int | None = None


def _check_filters(data: ScheduleInput) -> None:
    """Themes narrow the categories and regions widen the countries; both are bounded."""
    if len(data.categories) > MAX_THEMES or len(set(data.categories)) != len(data.categories):
        raise InvalidRequest(f"Choose up to {MAX_THEMES} distinct themes.")
    try:
        normalise_regions(data.regions)
    except ValueError as exc:
        raise InvalidRequest(str(exc)) from exc


def _research_question(data: ScheduleInput) -> str | None:
    if data.research_focus in (ResearchFocus.DOCUMENT, ResearchFocus.MEDIA):
        raise InvalidRequest(
            "Document and media inputs expire and cannot be scheduled. "
            "Use an interactive follow-up on the saved report instead."
        )
    question = data.question.strip() if data.question else None
    _check_filters(data)
    maximum = 2000 if data.brief_id is not None else 1000
    if question is not None and not 1 <= len(question) <= maximum:
        raise InvalidRequest(f"A question needs between 1 and {maximum} characters.")
    if data.research_mode is not None and not question:
        raise InvalidRequest("On-demand research requires a saved question.")
    if data.research_mode is not None and data.research_mode not in ResearchMode:
        raise InvalidRequest("Unknown research mode.")
    if (
        data.research_mode
        and data.research_focus != ResearchFocus.GENERAL
        and (data.country_iso or data.country_isos)
    ):
        raise InvalidRequest("Focused research uses its subject scope, not a nation filter.")
    if data.research_focus not in ResearchFocus:
        raise InvalidRequest("Unknown research focus.")
    if not 1 <= len(data.research_languages) <= 8 or any(
        re.fullmatch(r"[a-z]{2,3}(-[a-z]{2,4})?", code.lower()) is None
        for code in data.research_languages
    ):
        raise InvalidRequest("Provide between one and eight language codes.")
    if data.research_subject is not None and len(data.research_subject) > 300:
        raise InvalidRequest("The research subject must not exceed 300 characters.")
    if (
        data.research_mode
        and data.research_focus in (ResearchFocus.COMPANY, ResearchFocus.DOMAIN)
        and (not data.research_subject or not data.research_subject.strip())
    ):
        raise InvalidRequest("Focused research needs an organisation or domain subject.")
    if (data.research_web_search or data.research_source_ids is not None) and (
        data.research_mode is None or not question
    ):
        raise InvalidRequest("Web search and source choices require a saved research question.")
    sources = data.research_source_ids
    if sources is not None and (
        len(sources) > 64
        or len(set(sources)) != len(sources)
        or any(not source.strip() or len(source) > 120 for source in sources)
    ):
        raise InvalidRequest("Choose up to 64 unique research source identifiers.")
    return question


def build_schedule(  # noqa: PLR0912
    data: ScheduleInput,
    *,
    schedule_id: UUID,
    owner: UUID,
    created: datetime,
    now: datetime,
    previous: Schedule | None = None,
) -> Schedule:
    name = " ".join(data.name.split())
    if not name:
        raise InvalidRequest("A schedule needs a name.")
    template = TEMPLATES.get(data.template_id)
    if template is None:
        raise InvalidRequest("Unknown report template.")
    validate_subscription_scope(data, template)
    question = _research_question(data)
    if template.needs_question and data.plan_id is None and not question:
        raise InvalidRequest("Ask the Eye needs a question or collection plan.")
    try:
        countries = normalise_countries(data.country_iso, data.country_isos)
    except ValueError as exc:
        raise InvalidRequest(str(exc)) from exc
    country = countries[0] if len(countries) == 1 else None
    if template.needs_country and len(countries) != 1:
        raise InvalidRequest("This product needs exactly one nation.")
    if not (0 <= data.hour_utc <= 23):
        raise InvalidRequest("The hour must be between 0 and 23 UTC.")
    if data.cadence not in CADENCES:
        raise InvalidRequest("Choose a supported daily, weekly or calendar-month subscription.")
    if not (0 <= data.weekday <= 6):
        raise InvalidRequest("The weekday must be between 0 (Monday) and 6 (Sunday).")
    if not (1 <= data.monthday <= 31):
        raise InvalidRequest("The day of the month must be between 1 and 31.")
    if not (1 <= data.anchor_month <= 12):
        raise InvalidRequest("The anchor month must be between 1 and 12.")
    if data.window_hours is not None and not (1 <= data.window_hours <= MAX_WINDOW_HOURS):
        raise InvalidRequest("The lookback must be between 1 hour and 730 days.")
    try:
        recurrence = LocalRecurrence(
            data.timezone,
            data.hour_utc if data.local_hour is None else data.local_hour,
            data.local_minute,
            data.cadence,
            data.weekday,
            data.monthday,
            data.anchor_month,
        )
    except ValueError as exc:
        raise InvalidRequest(str(exc)) from exc
    if not isinstance(data.collection_policy, WindowPolicy):
        raise InvalidRequest("Choose a supported collection window policy.")
    if (data.brief_id is None) != (data.brief_revision is None) or (
        data.brief_revision is not None and data.brief_revision < 1
    ):
        raise InvalidRequest("A linked Research Brief needs an exact positive revision.")
    if data.notify_on_change and not question and data.plan_id is None:
        raise InvalidRequest("Change monitoring requires a saved question or collection plan.")
    reset = (
        previous is None
        or previous.country_isos != countries
        or any(
            getattr(previous, key) != getattr(data, key)
            for key in (
                "question",
                "research_mode",
                "research_languages",
                "research_focus",
                "research_subject",
                "research_web_search",
                "research_source_ids",
                "plan_id",
                "window_hours",
                "template_id",
                "notify_on_change",
                "conflict_id",
                "hazard",
                "categories",
                "regions",
                "research_area",
                "avoid_repetition",
                "collection_policy",
                "brief_id",
                "brief_revision",
            )
        )
    )
    reschedule = previous is None or any(
        getattr(previous, key) != getattr(data, key)
        for key in (
            "hour_utc",
            "cadence",
            "weekday",
            "monthday",
            "anchor_month",
            "timezone",
            "local_minute",
        )
    )
    reschedule = reschedule or (previous is not None and previous.local_hour != recurrence.hour)
    next_run_at = recurrence.preview(now, 1)[0].utc
    if previous is not None and not reschedule:
        rebased = rebased_next_run(previous, now) if data.enabled and not previous.enabled else None
        next_run_at = rebased or previous.next_run_at
    return Schedule(
        id=schedule_id,
        name=name[:120],
        template_id=template.id,
        country_iso=country,
        country_isos=countries,
        plan_id=data.plan_id,
        hour_utc=data.hour_utc,
        cadence=data.cadence,
        weekday=data.weekday,
        window_hours=data.window_hours,
        enabled=data.enabled,
        created_by=owner,
        created_at=created,
        next_run_at=next_run_at,
        last_run_at=None if previous is None else previous.last_run_at,
        last_report_id=None if reset or previous is None else previous.last_report_id,
        last_error=None if reset or previous is None else previous.last_error,
        team_id=data.team_id,
        notify_on_change=data.notify_on_change,
        last_change=None if reset or previous is None else previous.last_change,
        question=question,
        research_mode=data.research_mode,
        research_languages=tuple(dict.fromkeys(code.lower() for code in data.research_languages)),
        research_focus=data.research_focus,
        research_subject=data.research_subject.strip() or None if data.research_subject else None,
        monthday=data.monthday,
        research_web_search=data.research_web_search,
        research_source_ids=data.research_source_ids,
        anchor_month=data.anchor_month,
        conflict_id=data.conflict_id,
        hazard=data.hazard,
        categories=tuple(data.categories),
        regions=normalise_regions(data.regions),
        research_area=data.research_area,
        disclose_area_to_provider=data.disclose_area_to_provider,
        avoid_repetition=data.avoid_repetition,
        seen_content_signatures=()
        if reset or previous is None
        else previous.seen_content_signatures,
        baseline_report_id=None if reset or previous is None else previous.baseline_report_id,
        last_version_id=None if reset or previous is None else previous.last_version_id,
        last_outcome=None if reset or previous is None else previous.last_outcome,
        last_coverage=None if reset or previous is None else previous.last_coverage,
        timezone=data.timezone,
        local_hour=recurrence.hour,
        local_minute=data.local_minute,
        collection_policy=data.collection_policy,
        brief_id=data.brief_id,
        brief_revision=data.brief_revision,
    )
