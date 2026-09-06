"""Resolve authorised destination scope once, before any external model work.

Assignments apply to all text roles. A broken assignment never falls back to another
team's provider. Historical first-enabled selection is confined to installations without
any assignment. Embeddings are a separate explicit role, never a text assignment.
"""

from dataclasses import dataclass, field, fields
from typing import Any
from uuid import UUID

from ase.application.ports.llm import LlmBindingRepository, LlmProfileRepository
from ase.domain.errors import NoModelAvailable
from ase.domain.llm import TEXT_ROLES, LlmProfile, LlmRole
from ase.domain.model_routing import ModelRoutingRecord, RoutedModel

UNAVAILABLE = "The assigned model is unavailable or its tested configuration has changed."


@dataclass(frozen=True, slots=True)
class RoleProfiles:
    """Immutable settings, including credentials privately held only for this run.

    Callers receive independent profile objects. Later repository edits, rebinding or
    mutation by a consumer cannot change the settings used by another stage.
    """

    provenance: ModelRoutingRecord
    _settings: tuple[tuple[LlmRole, tuple[tuple[str, Any], ...]], ...] = field(repr=False)

    async def profile_for(self, role: LlmRole) -> LlmProfile | None:
        return self._get(role)

    def required(self, role: LlmRole) -> LlmProfile:
        profile = self._get(role)
        if profile is None:
            raise NoModelAvailable()
        return profile

    def _get(self, role: LlmRole) -> LlmProfile | None:
        for selected_role, settings in self._settings:
            if role == selected_role:
                return LlmProfile(**dict(settings))
        return None


class ModelRouting:
    def __init__(
        self, profiles: LlmProfileRepository, bindings: LlmBindingRepository | None = None
    ) -> None:
        self._profiles = profiles
        self._bindings = bindings

    async def snapshot(
        self,
        *,
        team_id: UUID | None = None,
        profile_id: UUID | None = None,
        role: LlmRole = LlmRole.ASSESSMENT,
    ) -> RoleProfiles:
        # One binding-table read avoids mixing team/global decisions from different reads.
        bindings = await self._bindings.list_all() if self._bindings is not None else []
        binding = next((item for item in bindings if item.team_id == team_id), None)
        if binding is None and team_id is not None:
            binding = next((item for item in bindings if item.team_id is None), None)
        selected: dict[LlmRole, LlmProfile] = {}
        if binding is not None:
            profile = await self._profiles.get(binding.profile_id)
            if (
                profile is None
                or not all(profile.allows(text_role) for text_role in TEXT_ROLES)
                or binding.profile_revision != profile.revision
                or binding.tested_config_hash != profile.config_hash
            ):
                raise NoModelAvailable(UNAVAILABLE)
            selected = dict.fromkeys(TEXT_ROLES, profile)
        elif bindings:
            raise NoModelAvailable("No global model is assigned and this team has no override.")
        else:
            for candidate in await self._profiles.list_all():
                for text_role in TEXT_ROLES:
                    if candidate.allows(text_role):
                        selected.setdefault(text_role, candidate)
            if profile_id is not None:
                chosen = await self._profiles.get(profile_id)
                if chosen is None or role not in TEXT_ROLES or not chosen.allows(role):
                    raise NoModelAvailable()
                selected[role] = chosen
        if role not in selected:
            raise NoModelAvailable()
        provenance = ModelRoutingRecord(
            policy="legacy"
            if binding is None
            else ("global" if binding.team_id is None else "team"),
            destination_team_id=team_id,
            binding_team_id=binding.team_id if binding else None,
            profiles=tuple(
                RoutedModel(
                    role=selected_role,
                    profile_id=profile.id,
                    profile_revision=profile.revision,
                    model=profile.model,
                    reasoning_effort=profile.reasoning_effort,
                    max_output_tokens=profile.max_output_tokens,
                    temperature=profile.temperature,
                    profile_updated_at=profile.updated_at,
                )
                for selected_role, profile in sorted(selected.items())
            ),
        )
        return RoleProfiles(
            provenance,
            tuple(
                (key, tuple((item.name, getattr(value, item.name)) for item in fields(value)))
                for key, value in selected.items()
            ),
        )

    async def embeddings(self) -> LlmProfile | None:
        """Separate global embeddings role; no text binding can redirect shared indexing."""
        bindings = await self._bindings.list_all() if self._bindings is not None else []
        team_only = {item.profile_id for item in bindings if item.team_id is not None} - {
            item.profile_id for item in bindings if item.team_id is None
        }
        for profile in await self._profiles.list_all():
            if profile.id not in team_only and profile.allows(LlmRole.EMBEDDINGS):
                return LlmProfile(
                    **{item.name: getattr(profile, item.name) for item in fields(profile)}
                )
        return None
