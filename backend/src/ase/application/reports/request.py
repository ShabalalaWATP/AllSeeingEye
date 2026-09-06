"""What a report is asked to cover; regeneration rebuilds it from the stored scope."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from ase.domain.events import Category
from ase.domain.research import ResearchFocus, ResearchMode


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
    research_focus: ResearchFocus = ResearchFocus.GENERAL
    research_subject: str | None = None
    research_input_id: UUID | None = None
    parent_report_id: UUID | None = None
    parent_version: int | None = None
    report_language: Literal["en", "fr", "de", "es", "ar", "ru", "uk", "zh"] = "en"
    report_style: Literal["briefing", "assessment"] = "assessment"

    @classmethod
    def from_scope(cls, template_id: str, scope: Mapping[str, Any]) -> ReportRequest:
        categories = tuple(Category(str(c)) for c in scope.get("categories") or [])
        window = scope.get("window_hours")
        return cls(
            template_id=template_id,
            report_language=scope.get("report_language", "en"),
            report_style=scope.get("report_style", "assessment"),
            country_iso=scope.get("country") or None,
            categories=categories,
            question=scope.get("question") or None,
            window_hours=int(window) if window else None,
            devils_advocacy=bool(scope.get("devils_advocacy", False)),
            hazard=scope.get("hazard") or None,
            conflict_id=scope.get("conflict") or None,
            plan_id=UUID(str(scope["plan"])) if scope.get("plan") else None,
            research_mode=ResearchMode(scope["research_mode"])
            if scope.get("research_mode")
            else None,
            research_languages=tuple(scope.get("research_languages") or ("en",)),
            research_focus=ResearchFocus(scope.get("research_focus", "general")),
            research_subject=scope.get("research_subject") or None,
            parent_report_id=UUID(str(scope["parent_report_id"]))
            if scope.get("parent_report_id")
            else None,
            parent_version=int(scope["parent_version"]) if scope.get("parent_version") else None,
        )
