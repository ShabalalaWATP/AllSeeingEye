"""Administrator evaluation runs: packaged casebooks, durable run state and the runner."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import cached_property
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.evaluations.harness import PackagedEvaluationHarness
from ase.adapters.persistence.evaluation_runs import SqlEvaluationRunRepository
from ase.application.admin.evaluation_runner import EvaluationExecution, EvaluationTasks
from ase.application.admin.evaluations import EvaluationRuns
from ase.application.ports.evaluations import EvaluationUnit
from ase.container.core import ContainerCore


class EvaluationWiring(ContainerCore):
    @cached_property
    def evaluation_harness(self) -> PackagedEvaluationHarness:
        return PackagedEvaluationHarness()

    @cached_property
    def evaluation_tasks(self) -> EvaluationTasks:
        return EvaluationTasks(self._execute_evaluation)

    def evaluation_run_repository(self, session: AsyncSession) -> SqlEvaluationRunRepository:
        return SqlEvaluationRunRepository(session)

    def evaluation_runs(self, session: AsyncSession) -> EvaluationRuns:
        r = self.repositories(session)
        return EvaluationRuns(
            self.evaluation_run_repository(session),
            r.llm_profiles,
            self.evaluation_harness,
            self.cipher,
            self.access_policy(session),
            self.clock,
            r.uow,
            self.evaluation_tasks,
        )

    async def _execute_evaluation(self, run_id: UUID) -> None:
        # Built per run so it uses the gateway configured when the run starts.
        execution = EvaluationExecution(
            self._evaluation_unit,
            self.evaluation_harness,
            self.llm,
            self.cipher,
            self.clock,
            self.ai_usage_accounting,
        )
        await execution.execute(run_id)

    @asynccontextmanager
    async def _evaluation_unit(self) -> AsyncIterator[EvaluationUnit]:
        async with self.session_factory() as session:
            r = self.repositories(session)
            yield EvaluationUnit(
                SqlEvaluationRunRepository(session),
                r.llm_profiles,
                self.access_policy(session),
                r.uow,
            )
