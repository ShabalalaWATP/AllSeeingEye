"""Copy a pinned preset into an editable canonical definition; never save or dispatch it."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from ase.application.research.brief_codec import brief_to_dict
from ase.application.research.presets_readiness import PresetReadiness
from ase.application.research.presets_schema import LENS_RULE, ResearchPreset
from ase.domain.research import ResearchMode
from ase.domain.research_brief import ResearchBrief
from ase.domain.research_brief_scope import BriefCollection, BriefObservation, BriefScope
from ase.domain.research_brief_values import (
    BriefIdentity,
    BriefIndicator,
    BriefLens,
    BriefLimits,
    BriefMonitoring,
    BriefOutput,
    BriefQuestion,
    BriefValidationError,
    IntelligenceRequirement,
    LensId,
)
from ase.domain.research_capacity import MAX_SELECTED_SOURCES


def preset_definition(
    preset: ResearchPreset,
    readiness: PresetReadiness,
    *,
    depth: ResearchMode = ResearchMode.DETAILED,
    lens: LensId | None = None,
    selected_requirement_ids: tuple[str, ...] | None = None,
    selected_source_ids: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Keep missing subject/area inputs visible in the accompanying readiness record.

    A Basic reduction requires an explicit selection. An oversized source pool
    produces an empty selected-only definition requiring user selection, never
    a silently truncated list or a wider all-eligible policy.
    """
    selected_lens = lens or preset.default_lens
    if selected_lens not in preset.lens_choices:
        raise BriefValidationError("lens.id", "Choose a lens supported by this preset")
    requirements = preset.requirements
    if selected_requirement_ids is not None:
        if (
            not selected_requirement_ids
            or len(set(selected_requirement_ids)) != len(selected_requirement_ids)
            or not set(selected_requirement_ids) <= {row.id for row in requirements}
        ):
            raise BriefValidationError("question.requirements", "Choose valid unique requirements")
        requirements = tuple(row for row in requirements if row.id in selected_requirement_ids)
    candidates = readiness.candidate_provider_ids
    sources = () if readiness.source_selection_required else candidates
    if selected_source_ids is not None:
        if (
            len(selected_source_ids) > MAX_SELECTED_SOURCES
            or len(set(selected_source_ids)) != len(selected_source_ids)
            or not set(selected_source_ids) <= set(candidates)
        ):
            raise BriefValidationError("collection.source_ids", "Choose current candidate sources")
        sources = selected_source_ids
    # These temporary identities only exercise the canonical schema. They never
    # enter the returned editable definition or any persistence/API response.
    at = datetime(2000, 1, 1, tzinfo=UTC)
    brief = ResearchBrief(
        identity=BriefIdentity(
            UUID(int=0),
            1,
            UUID(int=0),
            preset.title,
            at,
            at,
            preset_id=preset.id,
            preset_version=preset.version,
        ),
        question=BriefQuestion(
            preset.question,
            tuple(
                IntelligenceRequirement(row.id, row.question, row.required, row.priority)
                for row in requirements
            ),
            preset.exclusions,
        ),
        scope=BriefScope(country_isos=preset.country_isos),
        observation=BriefObservation(
            "relative",
            lookback_hours=preset.baseline_days * 24,
            forecast_horizon_days=preset.forecast_horizon_days,
        ),
        lens=BriefLens(
            selected_lens,
            relevance_instructions=f"{LENS_RULE}\nScope and coverage: {preset.scope_note}",
            challenge_conclusions=True,
        ),
        collection=BriefCollection(
            languages=preset.suggested_languages,
            source_policy="selected_only",
            source_ids=sources,
            require_primary=True,
            require_opposition=True,
        ),
        output=BriefOutput(depth, preferred_sections=preset.sections),
        limits=BriefLimits(),
        monitoring=BriefMonitoring(
            tuple(BriefIndicator(row.id, row.condition) for row in preset.indicators),
            review_conditions=(
                "Review cited observable conditions; these are not verified alerts.",
            ),
        ),
    )
    definition = brief_to_dict(brief)
    definition.pop("identity")
    return {
        "title": preset.title,
        "team_id": None,
        "preset_id": preset.id,
        "preset_version": preset.version,
        **definition,
    }
