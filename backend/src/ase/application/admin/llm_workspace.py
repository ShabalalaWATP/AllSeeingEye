"""Apply the assignment matrix atomically under the shared administration guard."""

from dataclasses import dataclass

from ase.application.access import AccessContext, AccessPolicy
from ase.application.admin.llm_connections import ConnectionInput, LlmConnectionsUseCase
from ase.application.admin.llm_workspace_allowances import WorkspaceAllowances
from ase.application.admin.llm_workspace_inputs import WorkspaceChange
from ase.application.dto import RequestContext
from ase.application.policy import require_admin
from ase.application.ports import UnitOfWork
from ase.application.ports.repositories import UserRepository
from ase.application.ports.session import SessionCheck
from ase.domain.ai_usage import AiUsagePolicy
from ase.domain.errors import InvalidRequest, NotFound
from ase.domain.llm import LlmConnectionBinding
from ase.domain.users import User


@dataclass(frozen=True, slots=True)
class WorkspaceResult:
    connections: list[LlmConnectionBinding]
    policies: list[AiUsagePolicy]


class LlmWorkspaceUseCase:
    def __init__(
        self,
        connections: LlmConnectionsUseCase,
        allowances: WorkspaceAllowances,
        access: AccessPolicy,
        users: UserRepository,
        uow: UnitOfWork,
    ) -> None:
        self.connections, self.allowances, self.access = connections, allowances, access
        self.users, self.uow = users, uow

    async def execute(
        self,
        actor: User,
        changes: list[WorkspaceChange],
        context: RequestContext,
        *,
        before_save: SessionCheck | None = None,
    ) -> WorkspaceResult:
        if not 1 <= len(changes) <= 100:
            raise InvalidRequest("Apply between one and 100 workspace changes at a time.")
        if len({(change.scope, change.target_id) for change in changes}) != len(changes):
            raise InvalidRequest("Each workspace can appear only once in an update.")
        try:
            access = await self.access.context(actor, for_update=True)
            require_admin(access.actor)
            for change in changes:
                await self._validate_target(change, access)
            await self.allowances.lock(changes)
            # A new global default may be established alongside dependent overrides.
            for change in sorted(changes, key=lambda item: item.scope != "global"):
                if change.model is not None:
                    await self._apply_model(access.actor, change, context)
                if change.allowance is not None:
                    await self.allowances.apply(access.actor, change, context)
            result = WorkspaceResult(
                await self.connections.list(access.actor),
                await self.allowances.repository.list_policies(),
            )
            if before_save is not None:
                await before_save()
            await self.uow.commit()
            return result
        except BaseException:
            await self.uow.rollback()
            raise

    async def _validate_target(self, change: WorkspaceChange, access: AccessContext) -> None:
        if change.scope == "global":
            return
        if change.target_id is None:
            raise InvalidRequest("A team or personal workspace requires a target.")
        if change.scope == "team":
            target = access.teams.get(change.target_id)
            if target is None:
                raise NotFound()
            active = target.is_active
        else:
            user = await self.users.get_by_id(change.target_id)
            if user is None:
                raise NotFound()
            active = user.is_active
        if not active:
            raise InvalidRequest("Reactivate this account or team before changing its AI settings.")

    async def _apply_model(
        self, actor: User, change: WorkspaceChange, context: RequestContext
    ) -> None:
        data = change.model
        if data is None:
            return
        if data.profile_id is not None:
            if data.expected_profile_revision is None or data.tested_config_hash is None:
                raise InvalidRequest("Select a successfully tested model before applying it.")
            await self.connections.activate(
                actor,
                ConnectionInput(
                    change.target_id if change.scope == "team" else None,
                    data.profile_id,
                    data.expected_profile_revision,
                    data.tested_config_hash,
                    data.expected_binding_revision,
                    user_id=change.target_id if change.scope == "user" else None,
                ),
                context,
                commit=False,
            )
        else:
            if change.target_id is None or data.expected_binding_revision is None:
                raise InvalidRequest("Reload the current connection before removing an override.")
            reset = (
                self.connections.reset_team
                if change.scope == "team"
                else self.connections.reset_user
            )
            await reset(
                actor, change.target_id, data.expected_binding_revision, context, commit=False
            )
