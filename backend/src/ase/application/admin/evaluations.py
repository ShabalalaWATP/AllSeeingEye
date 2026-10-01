"""Administrator requests for evaluation runs: catalogue, start, cancel and downloads.

Starting and cancelling take the shared administration guard through AccessPolicy,
commit, and only then hand the run to the background launcher. No model call happens
while a request transaction or the guard is held.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID, uuid4

from ase.application.access import AccessPolicy
from ase.application.policy import require_admin
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.evaluations import EvaluationHarness, EvaluationRunRepository
from ase.application.ports.llm import LlmProfileRepository, SecretCipher
from ase.application.ports.session import SessionCheck
from ase.domain.errors import Conflict, EncryptionUnavailable, InvalidRequest, NotFound
from ase.domain.evaluations import (
    RETAINED_RUNS,
    RUN_LEASE,
    EvaluationCaseInfo,
    EvaluationRun,
    EvaluationRunStatus,
    EvaluationStopReason,
    checked_call_cap,
    selected_cases,
)
from ase.domain.llm import LlmRole
from ase.domain.users import User


class EvaluationLauncher(Protocol):
    def launch(self, run_id: UUID) -> None: ...

    def cancel(self, run_id: UUID) -> bool: ...


@dataclass(frozen=True, slots=True)
class EvaluationStart:
    profile_id: UUID
    case_ids: list[str]
    max_calls: int


class EvaluationRuns:
    def __init__(
        self,
        runs: EvaluationRunRepository,
        profiles: LlmProfileRepository,
        harness: EvaluationHarness,
        cipher: SecretCipher,
        access: AccessPolicy,
        clock: Clock,
        uow: UnitOfWork,
        launcher: EvaluationLauncher,
    ) -> None:
        self._runs, self._profiles, self._harness = runs, profiles, harness
        self._cipher, self._access, self._clock = cipher, access, clock
        self._uow, self._launcher = uow, launcher

    async def catalogue(self, actor: User) -> tuple[EvaluationCaseInfo, ...]:
        await self._admin(actor)
        return self._harness.catalogue()

    async def recent(self, actor: User) -> list[EvaluationRun]:
        await self._admin(actor)
        return await self._runs.recent(RETAINED_RUNS)

    async def get(self, actor: User, run_id: UUID) -> EvaluationRun:
        await self._admin(actor)
        return await self._existing(run_id)

    async def artefact(self, actor: User, run_id: UUID) -> tuple[EvaluationRun, bytes]:
        await self._admin(actor)
        run = await self._existing(run_id)
        content = await self._runs.artefact(run_id)
        if content is None:
            raise NotFound("This evaluation run has no download.")
        return run, content

    async def start(
        self, actor: User, request: EvaluationStart, *, before_save: SessionCheck | None = None
    ) -> EvaluationRun:
        await self._admin(actor, for_update=True)
        cases = selected_cases(request.case_ids, self._harness.catalogue())
        max_calls = checked_call_cap(request.max_calls)
        profile = await self._profiles.get(request.profile_id)
        if profile is None:
            raise NotFound("The AI connection was not found.")
        if LlmRole.ASSESSMENT not in profile.roles:
            raise InvalidRequest("Choose an AI connection configured for assessment.")
        if not self._cipher.available:
            raise EncryptionUnavailable()
        now = self._clock.now()
        current = await self._runs.active()
        if current is not None and current.lease_expired(now):
            # Its process stopped without finishing; the slot is released, never reused.
            await self._runs.finish(
                current.id,
                EvaluationRunStatus.STOPPED,
                EvaluationStopReason.INTERRUPTED,
                now,
                None,
            )
            current = None
        if current is not None:
            raise Conflict("An evaluation run is already in progress.")
        run = EvaluationRun(
            id=uuid4(),
            actor_id=actor.id,
            profile_id=profile.id,
            profile_name=profile.name,
            model=profile.model,
            profile_fingerprint=profile.config_hash,
            case_ids=tuple(case.id for case in cases),
            case_fingerprints={case.id: case.fingerprint for case in cases},
            max_calls=max_calls,
            status=EvaluationRunStatus.RUNNING,
            created_at=now,
            lease_expires_at=now + RUN_LEASE,
        )
        await self._runs.prune(RETAINED_RUNS - 1)
        await self._runs.add(run)
        if before_save is not None:
            await before_save()
        await self._uow.commit()
        self._launcher.launch(run.id)
        return run

    async def cancel(
        self, actor: User, run_id: UUID, *, before_save: SessionCheck | None = None
    ) -> EvaluationRun:
        await self._admin(actor, for_update=True)
        run = await self._existing(run_id)
        if not run.active:
            return run
        now = self._clock.now()
        # The durable flag stops a run owned by any process before its next call.
        await self._runs.request_cancel(run_id)
        if run.lease_expired(now):
            # Its process stopped without finishing; close it so it cannot block starts.
            await self._runs.finish(run_id, EvaluationRunStatus.CANCELLED, None, now, None)
        if before_save is not None:
            await before_save()
        await self._uow.commit()
        # Committed first, so the interrupted task records a cancellation, not a failure.
        self._launcher.cancel(run_id)
        return await self._existing(run_id)

    async def _admin(self, actor: User, *, for_update: bool = False) -> None:
        require_admin((await self._access.context(actor, for_update=for_update)).actor)

    async def _existing(self, run_id: UUID) -> EvaluationRun:
        run = await self._runs.get(run_id)
        if run is None:
            raise NotFound("The evaluation run was not found.")
        return run
