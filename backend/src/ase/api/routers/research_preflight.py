"""Private read-only preflight with current brief, source and session checks."""

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Response

from ase.api.deps import ContainerDep, CurrentUser, SessionDep
from ase.api.errors import InvalidQuery
from ase.api.schemas_research_preflight import ResearchPreflightOut
from ase.api.session_fence import FenceDep
from ase.application.research.preflight import preview_brief
from ase.application.research.presets import load_presets
from ase.application.research.presets_schema import ResearchPreset
from ase.application.source_capabilities import SourceCapabilityRegistry
from ase.container.research_capabilities import research_capability_registry
from ase.domain.research_brief_values import BriefValidationError

router = APIRouter(prefix="/research/briefs", tags=["research-preflight"])


@lru_cache(maxsize=1)
def _catalogue() -> tuple[SourceCapabilityRegistry, tuple[ResearchPreset, ...]]:
    registry = research_capability_registry()
    return registry, load_presets(registry)


@router.get("/{brief_id}/revisions/{revision}/preflight")
async def research_preflight(
    brief_id: UUID,
    revision: Annotated[int, Path(ge=1)],
    user: CurrentUser,
    session: SessionDep,
    fence: FenceDep,
    container: ContainerDep,
    response: Response,
) -> ResearchPreflightOut:
    access = await container.access_policy(session).context(user)
    brief = await container.research_briefs(session).get_authorised(access, brief_id, revision)
    registry, presets = _catalogue()
    preset = next(
        (
            row
            for row in presets
            if row.id == brief.identity.preset_id and row.version == brief.identity.preset_version
        ),
        None,
    )
    async with container.source_admission.guard():
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
        try:
            result = ResearchPreflightOut(
                preflight=preview_brief(
                    brief,
                    access,
                    now=container.clock.now(),
                    registry=registry,
                    enabled=enabled,
                    requirements=requirements,
                    bundle_ids=preset.source_bundles if preset is not None else (),
                )
            )
        except BriefValidationError as exc:
            raise InvalidQuery(
                "Review the saved brief before preflight.",
                fields={exc.field: "Invalid or unsupported choice."},
            ) from exc
        await fence.confirm(session=session)
        current = await container.access_policy(session).context(user)
        current.require_read(brief.identity.owner_id, brief.identity.team_id)
        fence.assert_live()
        response.headers["Cache-Control"] = "private, no-store"
        return result
