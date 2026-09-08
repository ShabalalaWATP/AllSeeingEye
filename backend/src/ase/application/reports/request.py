"""What a report is asked to cover; regeneration rebuilds it from the stored scope."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from ase.domain.events import Category
from ase.domain.evidence_time import EvidenceTimeBasis
from ase.domain.languages import ReportLanguage
from ase.domain.map_research_origin import MapResearchOrigin, origin_from_dict
from ase.domain.project_time import MAX_PROJECT_INTERVAL
from ase.domain.query_variant_records import required_variant, validate_variant_anchors
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_plan import QueryVariant
from ase.domain.research_tasks import (
    PlannedQueryTask,
    ResearchCandidate,
    candidate_from_dict,
    validate_operator_plan,
    validate_registry_scope,
)


@dataclass(frozen=True, slots=True)
class ReportRequest:
    template_id: str
    country_iso: str | None = None
    categories: tuple[Category, ...] = ()
    question: str | None = None
    window_hours: int | None = None
    profile_id: UUID | None = None
    devils_advocacy: bool = False
    hazard: str | None = None
    conflict_id: str | None = None
    plan_id: UUID | None = None
    team_id: UUID | None = None
    automation: bool = False
    research_mode: ResearchMode | None = None
    research_languages: tuple[str, ...] = ("en",)
    research_source_ids: tuple[str, ...] | None = None
    research_terms: tuple[str, ...] | None = None
    research_query_variants: tuple[QueryVariant, ...] = ()
    research_candidate_hypotheses: tuple[ResearchCandidate, ...] = ()
    research_planned_tasks: tuple[PlannedQueryTask, ...] = ()
    research_focus: ResearchFocus = ResearchFocus.GENERAL
    research_subject: str | None = None
    research_input_id: UUID | None = None
    parent_report_id: UUID | None = None
    parent_version: int | None = None
    report_language: ReportLanguage = "en"
    report_style: Literal["briefing", "assessment"] = "assessment"
    map_view_id: UUID | None = None
    map_revision_id: UUID | None = None
    disclose_area_to_provider: bool = False
    map_origin: MapResearchOrigin | None = None
    research_since: datetime | None = None
    research_until: datetime | None = None
    research_time_basis: EvidenceTimeBasis | None = None

    @property
    def effective_time_basis(self) -> EvidenceTimeBasis:
        return self.research_time_basis or (
            EvidenceTimeBasis.RESEARCH
            if self.map_view_id or self.map_origin
            else EvidenceTimeBasis.PUBLICATION
        )

    def __post_init__(self) -> None:
        validate_variant_anchors(self.research_query_variants, self.research_terms)
        if any(row.origin != "operator" for row in self.research_candidate_hypotheses) or any(
            row.origin != "operator" for row in self.research_planned_tasks
        ):
            raise ValueError("Report requests cannot claim model-generated planning provenance")
        validate_operator_plan(
            self.research_candidate_hypotheses,
            self.research_planned_tasks,
            self.research_source_ids,
        )
        validate_registry_scope(
            self.research_planned_tasks,
            self.research_focus is ResearchFocus.COMPANY
            and self.map_origin is None
            and self.map_view_id is None,
        )
        if (self.research_candidate_hypotheses or self.research_planned_tasks) and (
            self.research_mode is None
            or self.research_focus in {ResearchFocus.DOCUMENT, ResearchFocus.MEDIA}
        ):
            raise ValueError("Operator source tasks require public-source research")
        if self.research_time_basis is not None and not isinstance(
            self.research_time_basis, EvidenceTimeBasis
        ):
            raise ValueError("Invalid research time basis")
        recorded = self.research_time_basis is EvidenceTimeBasis.RECORDED
        if self.research_time_basis is not None and self.research_mode is None:
            raise ValueError("A research time basis requires research mode")
        if recorded and (
            self.research_since is None
            or self.research_until is None
            or self.research_focus is not ResearchFocus.GENERAL
            or self.parent_report_id is not None
        ):
            raise ValueError(
                "Project history requires an explicit interval and a new general research request"
            )
        if (self.map_view_id is None) != (self.map_revision_id is None):
            raise ValueError("Choose both saved map identifiers")
        if self.research_since is None and self.research_until is None:
            return
        if self.research_since is None or self.research_until is None:
            raise ValueError("Provide both research interval bounds")
        if any(value.utcoffset() is None for value in (self.research_since, self.research_until)):
            raise ValueError("Research interval bounds must include a timezone")
        maximum_days = MAX_PROJECT_INTERVAL.days if recorded else 14
        if (
            not timedelta(0)
            < self.research_until - self.research_since
            <= timedelta(days=maximum_days)
        ):
            raise ValueError(f"Research interval must be positive and at most {maximum_days} days")
        object.__setattr__(self, "research_since", self.research_since.astimezone(UTC))
        object.__setattr__(self, "research_until", self.research_until.astimezone(UTC))
        if self.window_hours is not None:
            raise ValueError("Choose a fixed research interval or a rolling window")
        if self.research_mode is None or (
            not recorded and (self.map_view_id is None or self.map_revision_id is None)
        ):
            raise ValueError(
                "Fixed research intervals require an exact saved map and research mode"
            )

    @classmethod
    def from_scope(cls, template_id: str, scope: Mapping[str, Any]) -> ReportRequest:
        categories = tuple(Category(str(c)) for c in scope.get("categories") or [])
        window = scope.get("window_hours")
        origin = origin_from_dict(scope.get("map_origin"))
        return cls(
            template_id=template_id,
            research_time_basis=EvidenceTimeBasis(scope["research_time_basis"])
            if scope.get("research_time_basis")
            else None,
            map_view_id=origin.view_id if origin else None,
            map_revision_id=origin.revision_id if origin else None,
            disclose_area_to_provider=scope.get("disclose_area_to_provider") is True,
            map_origin=origin,
            report_language=scope.get("report_language", "en"),
            report_style=scope.get("report_style", "assessment"),
            country_iso=scope.get("country") or None,
            categories=categories,
            question=scope.get("question") or None,
            window_hours=int(window) if window and not scope.get("research_since") else None,
            research_since=datetime.fromisoformat(str(scope["research_since"]))
            if scope.get("research_since")
            else None,
            research_until=datetime.fromisoformat(str(scope["research_until"]))
            if scope.get("research_until")
            else None,
            devils_advocacy=bool(scope.get("devils_advocacy", False)),
            hazard=scope.get("hazard") or None,
            conflict_id=scope.get("conflict") or None,
            plan_id=UUID(str(scope["plan"])) if scope.get("plan") else None,
            research_mode=ResearchMode(scope["research_mode"])
            if scope.get("research_mode")
            else None,
            research_languages=tuple(scope.get("research_languages") or ("en",)),
            research_source_ids=tuple(scope["research_source_ids"])
            if scope.get("research_source_ids") is not None
            else None,
            research_terms=tuple(scope["research_terms"])
            if scope.get("research_terms") is not None
            else None,
            research_query_variants=tuple(
                required_variant(row) for row in scope.get("research_query_variants", [])
            ),
            research_candidate_hypotheses=tuple(
                candidate_from_dict(row) for row in scope.get("research_candidate_hypotheses", ())
            ),
            research_planned_tasks=tuple(
                PlannedQueryTask(**{**row, "terms": tuple(row["terms"])})
                for row in scope.get("research_planned_tasks", ())
            ),
            research_focus=ResearchFocus(scope.get("research_focus", "general")),
            research_subject=scope.get("research_subject") or None,
            parent_report_id=UUID(str(scope["parent_report_id"]))
            if scope.get("parent_report_id")
            else None,
            parent_version=int(scope["parent_version"]) if scope.get("parent_version") else None,
        )
