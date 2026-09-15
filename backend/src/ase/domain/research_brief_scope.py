"""Bounded reusable Research Brief scope, time, collection and private references."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from ase.domain.events import Category
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.languages import valid_language_code
from ase.domain.map_research_origin import MapResearchOrigin
from ase.domain.query_variant_records import validate_variant_anchors
from ase.domain.research import ResearchFocus
from ase.domain.research_area import ResearchArea, validate_direct_area
from ase.domain.research_capacity import MAX_SELECTED_SOURCES
from ase.domain.research_plan import QueryVariant
from ase.domain.research_scope import (
    MAX_RESEARCH_HOURS,
    normalise_countries,
    validate_research_interval,
)
from ase.domain.research_tasks import (
    PlannedQueryTask,
    ResearchCandidate,
    validate_operator_plan,
)

from .research_brief_values import BriefValidationError, bounded_text, positive_version


@dataclass(frozen=True, slots=True)
class BriefScope:
    country_isos: tuple[str, ...] = ()
    focus: ResearchFocus = ResearchFocus.GENERAL
    subject: str | None = None
    reviewed_aliases: tuple[str, ...] = ()
    conflict_id: str | None = None
    hazard: str | None = None
    categories: tuple[Category, ...] = ()
    area: ResearchArea | None = None
    map_origin: MapResearchOrigin | None = None
    map_view_id: UUID | None = None
    map_revision_id: UUID | None = None
    disclose_area_to_provider: bool = False
    plan_id: UUID | None = None
    parent_report_id: UUID | None = None
    parent_version: int | None = None
    # Handoff provenance only. It does not impose the old report's interval or evidence.
    origin_report_id: UUID | None = None
    origin_version: int | None = None

    @property
    def effective_area(self) -> ResearchArea | None:
        return self.area or (self.map_origin.area if self.map_origin else None)

    @property
    def area_hash(self) -> str | None:
        area = self.effective_area
        return area.geometry.sha256 if area is not None else None

    @property
    def geometry_version(self) -> int | None:
        return 1 if self.effective_area is not None else None

    def __post_init__(self) -> None:  # noqa: PLR0912 - independent scope invariants
        if not isinstance(self.country_isos, tuple):
            raise BriefValidationError("scope.country_isos", "Choose a bounded country list")
        try:
            countries = normalise_countries(None, self.country_isos)
        except ValueError as exc:
            raise BriefValidationError("scope.country_isos", str(exc)) from exc
        object.__setattr__(self, "country_isos", countries)
        if not isinstance(self.focus, ResearchFocus):
            raise BriefValidationError("scope.focus", "Choose a supported research focus")
        if countries and self.focus is not ResearchFocus.GENERAL:
            raise BriefValidationError(
                "scope.country_isos", "Record-focused research has no country filter"
            )
        bounded_text(self.subject, "scope.subject", 300, optional=True)
        if self.focus in {ResearchFocus.COMPANY, ResearchFocus.DOMAIN} and self.subject is None:
            raise BriefValidationError("scope.subject", "Record-focused research needs a subject")
        if not isinstance(self.reviewed_aliases, tuple) or len(self.reviewed_aliases) > 16:
            raise BriefValidationError(
                "scope.reviewed_aliases", "Use at most sixteen reviewed aliases"
            )
        for alias in self.reviewed_aliases:
            bounded_text(alias, "scope.reviewed_aliases", 200)
        if self.subject is None and self.reviewed_aliases:
            raise BriefValidationError("scope.reviewed_aliases", "Aliases need a reviewed subject")
        bounded_text(self.conflict_id, "scope.conflict_id", 120, optional=True)
        bounded_text(self.hazard, "scope.hazard", 40, optional=True)
        if not isinstance(self.categories, tuple) or any(
            not isinstance(category, Category) for category in self.categories
        ):
            raise BriefValidationError("scope.categories", "Choose valid event categories")
        if self.area is not None:
            try:
                validate_direct_area(self.area)
            except ValueError as exc:
                raise BriefValidationError("scope.area", str(exc)) from exc
        if self.map_origin is not None and not isinstance(self.map_origin, MapResearchOrigin):
            raise BriefValidationError("scope.map_origin", "Invalid exact saved-map origin")
        if self.area is not None and self.map_origin is not None:
            raise BriefValidationError("scope.area", "Choose drawn area or saved-map origin")
        if (self.map_view_id is None) != (self.map_revision_id is None):
            raise BriefValidationError("scope.map_revision_id", "Pin both saved-map identifiers")
        if self.map_view_id is not None and (
            not isinstance(self.map_view_id, UUID)
            or not isinstance(self.map_revision_id, UUID)
            or self.area is not None
            or self.map_origin is not None
        ):
            raise BriefValidationError(
                "scope.map_view_id", "Choose one saved-map or drawn-area scope"
            )
        if type(self.disclose_area_to_provider) is not bool:
            raise BriefValidationError(
                "scope.disclose_area_to_provider", "Invalid area disclosure choice"
            )
        if self.plan_id is not None and not isinstance(self.plan_id, UUID):
            raise BriefValidationError("scope.plan_id", "Invalid collection-plan reference")
        if (self.parent_report_id is None) != (self.parent_version is None):
            raise BriefValidationError("scope.parent_version", "Pin both parent report and version")
        if self.parent_report_id is not None:
            if not isinstance(self.parent_report_id, UUID):
                raise BriefValidationError(
                    "scope.parent_report_id", "Invalid parent report reference"
                )
            positive_version(self.parent_version, "scope.parent_version")
        self._validate_origin()

    def _validate_origin(self) -> None:
        if (self.origin_report_id is None) != (self.origin_version is None):
            raise BriefValidationError("scope.origin_version", "Pin both origin report and version")
        if self.origin_report_id is not None:
            if not isinstance(self.origin_report_id, UUID):
                raise BriefValidationError(
                    "scope.origin_report_id", "Invalid origin report reference"
                )
            positive_version(self.origin_version, "scope.origin_version")


@dataclass(frozen=True, slots=True)
class BriefObservation:
    policy: Literal["explicit", "relative", "template_default"]
    since: datetime | None = None
    until: datetime | None = None
    lookback_hours: int | None = None
    time_basis: EvidenceTimeBasis | None = None
    forecast_horizon_days: int | None = None

    def __post_init__(self) -> None:
        if self.time_basis is not None and not isinstance(self.time_basis, EvidenceTimeBasis):
            raise BriefValidationError("observation.time_basis", "Invalid evidence time basis")
        if self.forecast_horizon_days is not None and (
            type(self.forecast_horizon_days) is not int
            or not 1 <= self.forecast_horizon_days <= 366
        ):
            raise BriefValidationError("observation.forecast_horizon_days", "Choose 1-366 days")
        if self.policy == "explicit":
            if self.since is None or self.until is None or self.lookback_hours is not None:
                raise BriefValidationError("observation", "Provide only an explicit start and end")
            try:
                validate_research_interval(
                    self.since,
                    self.until,
                    recorded=self.time_basis is EvidenceTimeBasis.RECORDED,
                )
            except (AttributeError, ValueError) as exc:
                raise BriefValidationError("observation.interval", str(exc)) from exc
            object.__setattr__(self, "since", self.since.astimezone(UTC))
            object.__setattr__(self, "until", self.until.astimezone(UTC))
        elif self.policy == "relative":
            if (
                self.since is not None
                or self.until is not None
                or type(self.lookback_hours) is not int
                or not 1 <= self.lookback_hours <= MAX_RESEARCH_HOURS
                or self.time_basis is EvidenceTimeBasis.RECORDED
            ):
                raise BriefValidationError(
                    "observation.lookback_hours", "Choose a bounded rolling window"
                )
        elif self.policy == "template_default":
            if self.since is not None or self.until is not None or self.lookback_hours is not None:
                raise BriefValidationError(
                    "observation", "Template default has no explicit interval"
                )
        else:
            raise BriefValidationError(
                "observation.policy", "Choose a supported observation policy"
            )

    def resolved_interval(self, now: datetime) -> tuple[datetime, datetime] | None:
        """Resolve rolling time only at admission; preserve the reusable definition."""
        if self.policy == "template_default":
            return None
        if self.policy == "explicit":
            if self.since is None or self.until is None:
                raise BriefValidationError("observation.interval", "Explicit interval is missing")
            return self.since, self.until
        if not isinstance(now, datetime) or now.utcoffset() is None:
            raise BriefValidationError("observation", "Admission needs an aware clock")
        if self.lookback_hours is None:
            raise BriefValidationError("observation.lookback_hours", "Rolling window is missing")
        until = now.astimezone(UTC)
        return until - timedelta(hours=self.lookback_hours), until


@dataclass(frozen=True, slots=True)
class BriefCollection:
    languages: tuple[str, ...] = ("en",)
    terms: tuple[str, ...] | None = None
    query_variants: tuple[QueryVariant, ...] = ()
    source_policy: Literal["all_eligible", "selected_only"] = "all_eligible"
    source_ids: tuple[str, ...] | None = None
    web_search: bool = False
    candidate_hypotheses: tuple[ResearchCandidate, ...] = ()
    planned_tasks: tuple[PlannedQueryTask, ...] = ()
    require_primary: bool = False
    require_local: bool = False
    require_opposition: bool = False

    def __post_init__(self) -> None:  # noqa: PLR0912 - independent collection invariants
        if (
            not isinstance(self.languages, tuple)
            or not 1 <= len(self.languages) <= 8
            or any(
                not isinstance(value, str) or not valid_language_code(value)
                for value in self.languages
            )
        ):
            raise BriefValidationError(
                "collection.languages", "Choose one to eight valid languages"
            )
        languages = tuple(dict.fromkeys(value.lower() for value in self.languages))
        if len(languages) != len(self.languages):
            raise BriefValidationError("collection.languages", "Language choices must be unique")
        object.__setattr__(self, "languages", languages)
        if self.terms is not None:
            if not isinstance(self.terms, tuple) or len(self.terms) > 12:
                raise BriefValidationError("collection.terms", "Use at most twelve search terms")
            for term in self.terms:
                bounded_text(term, "collection.terms", 300)
            if sum(map(len, self.terms)) > 1000:
                raise BriefValidationError(
                    "collection.terms", "Search terms exceed 1,000 characters"
                )
        if (
            not isinstance(self.query_variants, tuple)
            or len(self.query_variants) > 8
            or any(not isinstance(row, QueryVariant) for row in self.query_variants)
        ):
            raise BriefValidationError(
                "collection.query_variants", "Use at most eight query variants"
            )
        variant_languages = [row.language.lower() for row in self.query_variants]
        if len(set(variant_languages)) != len(variant_languages) or not set(
            variant_languages
        ).issubset(languages):
            raise BriefValidationError(
                "collection.query_variants", "Variants need unique selected languages"
            )
        try:
            validate_variant_anchors(self.query_variants, self.terms)
        except ValueError as exc:
            raise BriefValidationError("collection.query_variants", str(exc)) from exc
        if self.source_policy not in ("all_eligible", "selected_only") or (
            (self.source_policy == "all_eligible") != (self.source_ids is None)
        ):
            raise BriefValidationError(
                "collection.source_policy", "Match source policy to its selected IDs"
            )
        if self.source_ids is not None:
            if (
                not isinstance(self.source_ids, tuple)
                or len(self.source_ids) > MAX_SELECTED_SOURCES
            ):
                raise BriefValidationError("collection.source_ids", "Select at most 64 sources")
            for source_id in self.source_ids:
                bounded_text(source_id, "collection.source_ids", 120)
            if len(set(self.source_ids)) != len(self.source_ids):
                raise BriefValidationError("collection.source_ids", "Source IDs must be unique")
        for field in ("web_search", "require_primary", "require_local", "require_opposition"):
            if type(getattr(self, field)) is not bool:
                raise BriefValidationError(
                    f"collection.{field}", "Choose an explicit collection policy"
                )
        try:
            validate_operator_plan(self.candidate_hypotheses, self.planned_tasks, self.source_ids)
        except ValueError as exc:
            raise BriefValidationError("collection.planned_tasks", str(exc)) from exc


@dataclass(frozen=True, slots=True)
class BriefPrivateInput:
    """Only a reference. Session imports require renewed authority on every admission."""

    kind: Literal["session", "durable_report"]
    input_id: UUID | None = None
    report_id: UUID | None = None
    report_version: int | None = None
    expires_at: datetime | None = None
    disclose_to_provider: bool = False

    @property
    def requires_renewal(self) -> bool:
        return self.kind == "session"

    def __post_init__(self) -> None:
        if type(self.disclose_to_provider) is not bool:
            raise BriefValidationError(
                "private_inputs.disclose_to_provider", "Invalid disclosure choice"
            )
        if self.kind == "session":
            if (
                not isinstance(self.input_id, UUID)
                or self.report_id is not None
                or self.report_version is not None
            ):
                raise BriefValidationError(
                    "private_inputs.input_id", "Session input needs one exact input ID"
                )
            if self.expires_at is not None:
                if not isinstance(self.expires_at, datetime) or self.expires_at.utcoffset() is None:
                    raise BriefValidationError(
                        "private_inputs.expires_at", "Use an aware expiry date"
                    )
                object.__setattr__(self, "expires_at", self.expires_at.astimezone(UTC))
        elif self.kind == "durable_report":
            if (
                self.input_id is not None
                or not isinstance(self.report_id, UUID)
                or self.expires_at is not None
            ):
                raise BriefValidationError(
                    "private_inputs.report_id", "Use an exact durable report reference"
                )
            positive_version(self.report_version, "private_inputs.report_version")
        else:
            raise BriefValidationError("private_inputs.kind", "Unknown private input reference")
