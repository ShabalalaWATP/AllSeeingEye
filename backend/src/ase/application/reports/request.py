"""What a report is asked to cover; regeneration rebuilds it from the stored scope."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from ase.domain.events import Category


@dataclass(frozen=True, slots=True)
class ReportRequest:
    template_id: str
    country_iso: str | None = None
    categories: tuple[Category, ...] = ()
    question: str | None = None
    window_hours: int | None = None
    profile_id: UUID | None = None
    devils_advocacy: bool = False

    @classmethod
    def from_scope(cls, template_id: str, scope: Mapping[str, Any]) -> ReportRequest:
        categories = tuple(Category(str(c)) for c in scope.get("categories") or [])
        window = scope.get("window_hours")
        return cls(
            template_id=template_id,
            country_iso=scope.get("country") or None,
            categories=categories,
            question=scope.get("question") or None,
            window_hours=int(window) if window else None,
            devils_advocacy=bool(scope.get("devils_advocacy", False)),
        )
