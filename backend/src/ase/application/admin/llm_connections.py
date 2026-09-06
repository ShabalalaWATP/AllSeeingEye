"""Explicit activation of a tested text connection for a global or team audience."""

from dataclasses import dataclass
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.admin.llm_testing import SessionCheck
from ase.application.auditing import Auditor
from ase.application.dto import RequestContext
from ase.application.policy import require_admin
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.llm import LlmBindingRepository, LlmProfileRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.llm import TEXT_ROLES, LlmConnectionBinding
from ase.domain.users import User


@dataclass(frozen=True, slots=True)
class ConnectionInput:
    team_id: UUID | None
    profile_id: UUID
    expected_profile_revision: int
    tested_config_hash: str
    expected_binding_revision: int | None


class LlmConnectionsUseCase:
    def __init__(
        self,
        profiles: LlmProfileRepository,
        bindings: LlmBindingRepository,
        access: AccessPolicy,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self._profiles, self._bindings, self._access = profiles, bindings, access
        self._clock, self._auditor, self._uow = clock, auditor, uow

    async def list(self, actor: User) -> list[LlmConnectionBinding]:
        require_admin((await self._access.context(actor)).actor)
        return await self._bindings.list_all()

    async def activate(
        self,
        actor: User,
        data: ConnectionInput,
        context: RequestContext,
        *,
        before_save: SessionCheck | None = None,
    ) -> LlmConnectionBinding:
        access = await self._access.context(actor, for_update=True)
        require_admin(access.actor)
        if data.team_id is not None:
            team = access.teams.get(data.team_id)
            if team is None:
                raise NotFound()
            if not team.is_active:
                raise InvalidRequest("Reactivate the team before applying an AI connection.")
            if await self._bindings.get(None) is None:
                raise InvalidRequest(
                    "Apply a global AI connection before creating a team override."
                )
        profile = await self._profiles.get(data.profile_id)
        if profile is None:
            raise NotFound()
        if (
            not profile.is_tested
            or profile.revision != data.expected_profile_revision
            or profile.tested_config_hash != data.tested_config_hash
        ):
            raise InvalidRequest(
                "The saved profile does not match this successful test. Test it again."
            )
        if not TEXT_ROLES.issubset(profile.roles):
            raise InvalidRequest(
                "A default connection must support direction, assessment, devil and translation."
            )
        current = await self._bindings.get(data.team_id)
        if (current.revision if current else None) != data.expected_binding_revision:
            raise InvalidRequest("This audience's connection changed. Reload before applying it.")
        if before_save is not None:
            await before_save()
        # Activation changes operational availability, not the tested request settings.
        profile.enabled = True
        await self._profiles.save(profile)
        binding = LlmConnectionBinding(
            data.team_id,
            profile.id,
            profile.revision,
            data.tested_config_hash,
            self._clock.now(),
            actor.id,
            await self._bindings.next_revision(),
        )
        await self._bindings.save(binding)
        await self._auditor.record(
            AuditAction.LLM_CONNECTION_ACTIVATED,
            actor=actor.id,
            subject=str(profile.id),
            ip=context.ip,
            details={
                "team_id": str(data.team_id) if data.team_id else None,
                "profile_revision": profile.revision,
                "binding_revision": binding.revision,
            },
        )
        await self._uow.commit()
        return binding

    async def reset_team(
        self,
        actor: User,
        team_id: UUID,
        expected_revision: int,
        context: RequestContext,
        *,
        before_save: SessionCheck | None = None,
    ) -> None:
        access = await self._access.context(actor, for_update=True)
        require_admin(access.actor)
        if team_id not in access.teams:
            raise NotFound()
        current = await self._bindings.get(team_id)
        if current is None:
            raise NotFound()
        if current.revision != expected_revision:
            raise InvalidRequest("This audience's connection changed. Reload before resetting it.")
        if before_save is not None:
            await before_save()
        await self._bindings.delete(team_id)
        await self._auditor.record(
            AuditAction.LLM_CONNECTION_RESET,
            actor=actor.id,
            subject=str(team_id),
            ip=context.ip,
            details={"previous_profile_id": str(current.profile_id)},
        )
        await self._uow.commit()
