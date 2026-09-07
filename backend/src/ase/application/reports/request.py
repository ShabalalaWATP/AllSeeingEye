"""What a report is asked to cover; regeneration rebuilds it from the stored scope."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from ase.domain.events import Category
from ase.domain.languages import ReportLanguage
from ase.domain.map_research_origin import MapResearchOrigin, origin_from_dict
from ase.domain.research import ResearchFocus, ResearchMode
from ase.domain.research_plan import QueryVariant


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

    def __post_init__(self) -> None:
        if self.research_since is None and self.research_until is None:
            return
        if self.research_since is None or self.research_until is None:
            raise ValueError("Provide both research interval bounds")
        if any(value.utcoffset() is None for value in (self.research_since, self.research_until)):
            raise ValueError("Research interval bounds must include a timezone")
        if not timedelta(0) < self.research_until - self.research_since <= timedelta(days=14):
            raise ValueError("Research interval must be positive and at most 14 days")
        object.__setattr__(self, "research_since", self.research_since.astimezone(UTC))
        object.__setattr__(self, "research_until", self.research_until.astimezone(UTC))
        if self.window_hours is not None:
            raise ValueError("Choose a fixed research interval or a rolling window")
        if self.map_view_id is None or self.map_revision_id is None or self.research_mode is None:
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
                QueryVariant(row["language"], tuple(row["terms"]))
                for row in scope.get("research_query_variants", [])
            ),
            research_focus=ResearchFocus(scope.get("research_focus", "general")),
            research_subject=scope.get("research_subject") or None,
            parent_report_id=UUID(str(scope["parent_report_id"]))
            if scope.get("parent_report_id")
            else None,
            parent_version=int(scope["parent_version"]) if scope.get("parent_version") else None,
        )
