"""Bounded process-local progress, private to the initiating identity generation."""

from dataclasses import replace
from datetime import timedelta
from uuid import UUID

from ase.application.ports import Clock
from ase.domain.errors import InvalidRequest, NotFound, RateLimited
from ase.domain.research_runs import ResearchRun, ResearchStage
from ase.domain.users import User

RUN_TTL_SECONDS = 1800
MAX_RUNS = 32
MAX_ACTIVE_PER_USER = 2


class ResearchRunStore:
    """Event-loop-only operations; progress is not a durable background job queue."""

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._runs: dict[UUID, ResearchRun] = {}

    def _expire(self) -> None:
        now = self._clock.now()
        self._runs = {key: run for key, run in self._runs.items() if run.expires_at > now}

    def reserve(self, actor: User, run_id: UUID) -> ResearchRun:
        self._expire()
        if not actor.is_active:
            raise NotFound()
        if run_id in self._runs:
            raise InvalidRequest("Use a new research run identifier for each request.")
        active = sum(
            run.owner_id == actor.id and not run.stage.terminal for run in self._runs.values()
        )
        if active >= MAX_ACTIVE_PER_USER:
            raise RateLimited(5)
        if len(self._runs) >= MAX_RUNS:
            # Completed progress can be evicted; active work is never displaced.
            terminal = [run for run in self._runs.values() if run.stage.terminal]
            if not terminal:
                raise RateLimited(5)
            oldest = min(terminal, key=lambda run: run.updated_at)
            del self._runs[oldest.id]
        now = self._clock.now()
        run = ResearchRun(
            run_id,
            actor.id,
            actor.security_version,
            ResearchStage.PLANNING,
            now,
            now,
            now + timedelta(seconds=RUN_TTL_SECONDS),
        )
        self._runs[run_id] = run
        return run

    def read(self, actor: User, run_id: UUID) -> ResearchRun:
        self._expire()
        run = self._runs.get(run_id)
        if (
            run is None
            or not actor.is_active
            or run.owner_id != actor.id
            or run.security_version != actor.security_version
        ):
            raise NotFound()
        return run

    def update(
        self, actor: User, run_id: UUID, stage: ResearchStage, report_id: UUID | None = None
    ) -> ResearchRun:
        run = self.read(actor, run_id)
        if run.stage.terminal:
            return run
        if (stage is ResearchStage.COMPLETED) != (report_id is not None):
            raise ValueError("Only completed research progress has a report identifier.")
        run = replace(run, stage=stage, updated_at=self._clock.now(), report_id=report_id)
        self._runs[run_id] = run
        return run
