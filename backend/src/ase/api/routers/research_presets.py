"""Authenticated read-only presets with current source and session checks on release."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Query, Response

from ase.api.deps import ClaimsDep, ContainerDep, CurrentUser, SessionDep
from ase.api.errors import InvalidQuery
from ase.api.schemas_research_briefs import ResearchBriefDraftIn
from ase.api.schemas_research_presets import (
    PresetDefinitionIn,
    PresetDefinitionOut,
    ResearchPresetOut,
    ResearchPresetsOut,
)
from ase.api.session_guard import validate_request_expiry, validate_request_session
from ase.application.research.presets import load_presets, pinned_preset, search_presets
from ase.application.research.presets_definition import preset_definition
from ase.application.research.presets_readiness import preset_readiness
from ase.application.research.presets_schema import PresetGroup, ResearchPreset
from ase.application.source_capabilities import SourceCapabilityRegistry
from ase.application.source_inventory import SourceRequirement
from ase.container.research_capabilities import research_capability_registry
from ase.domain.research_brief_values import BriefValidationError

router = APIRouter(prefix="/research/presets", tags=["research-presets"])


@lru_cache(maxsize=1)
def _catalogue() -> tuple[SourceCapabilityRegistry, tuple[ResearchPreset, ...]]:
    registry = research_capability_registry()
    return registry, load_presets(registry)


async def _source_context(
    container: ContainerDep, session: SessionDep
) -> tuple[dict[str, bool], dict[str, SourceRequirement]]:
    entries = await container.source_inventory(session).list()
    enabled = {
        row.spec.id: row.connection.enabled and not row.connection.environment_disabled
        for row in entries
    }
    requirements = {
        row.spec.id: row.connection.requirement
        for row in entries
        if row.connection.requirement is not None
    }
    return enabled, requirements


@router.get("")
async def list_presets(
    user: CurrentUser,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
    q: Annotated[str, Query(max_length=120)] = "",
    group: PresetGroup | None = None,
) -> ResearchPresetsOut:
    registry, presets = _catalogue()
    selected = search_presets(presets, query=q, group=group)
    async with container.source_admission.guard():
        enabled, requirements = await _source_context(container, session)
        result = ResearchPresetsOut(
            items=[
                ResearchPresetOut(
                    preset=preset,
                    readiness=preset_readiness(
                        preset, registry, enabled=enabled, requirements=requirements
                    ),
                )
                for preset in selected
            ]
        )
        await validate_request_session(container, claims, session=session)
        validate_request_expiry(container, claims)
        response.headers["Cache-Control"] = "private, no-store"
        return result


@router.post("/{preset_id}/definition")
async def editable_definition(
    preset_id: str,
    body: PresetDefinitionIn,
    user: CurrentUser,
    claims: ClaimsDep,
    container: ContainerDep,
    session: SessionDep,
    response: Response,
) -> PresetDefinitionOut:
    registry, presets = _catalogue()
    preset = pinned_preset(presets, preset_id, body.version)
    async with container.source_admission.guard():
        enabled, requirements = await _source_context(container, session)
        readiness = preset_readiness(preset, registry, enabled=enabled, requirements=requirements)
        try:
            definition = preset_definition(
                preset,
                readiness,
                depth=body.depth,
                lens=body.lens,
                selected_requirement_ids=body.selected_requirement_ids,
                selected_source_ids=body.selected_source_ids,
            )
        except BriefValidationError as exc:
            raise InvalidQuery(
                "Review the preset choices before continuing.",
                fields={exc.field: "Invalid or unsupported choice."},
            ) from exc
        selected = body.selected_requirement_ids
        result = PresetDefinitionOut(
            definition=ResearchBriefDraftIn.model_validate(definition),
            readiness=readiness,
            omitted_requirement_ids=[
                row.id
                for row in preset.requirements
                if selected is not None and row.id not in selected
            ],
        )
        await validate_request_session(container, claims, session=session)
        validate_request_expiry(container, claims)
        response.headers["Cache-Control"] = "private, no-store"
        return result
