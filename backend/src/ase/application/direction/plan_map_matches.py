"""Which live-store events a collection plan matches, for one reader's map filter.

This reuses the plan evidence read, so it inherits its object-level authorisation, its
seven-day window, its bounded query pool and its per-requirement cap. The result is a
sample computed on request: nothing is tagged in the feed pipeline, nothing is stored,
and private plan terms never enter the shared event stream.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ase.application.direction.plans import (
    EVIDENCE_WINDOW,
    PER_SIR,
    POOL,
    PlanEvidenceUseCase,
)
from ase.domain.collection import CollectionPlan, plan_matches
from ase.domain.users import User

WINDOW_HOURS = int(EVIDENCE_WINDOW.total_seconds() // 3600)


@dataclass(frozen=True, slots=True)
class EventMatch:
    event_id: str
    codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanMapMatches:
    plan: CollectionPlan
    considered: int
    truncated: bool
    matches: tuple[EventMatch, ...]


class PlanMapMatchesUseCase:
    def __init__(self, evidence: PlanEvidenceUseCase) -> None:
        self._evidence = evidence

    async def execute(self, actor: User, plan_id: UUID) -> PlanMapMatches:
        evidence = await self._evidence.execute(actor, plan_id)
        plan = evidence.plan
        seen: dict[str, EventMatch] = {}
        for sir in evidence.sirs:
            for event in sir.events:
                if event.id not in seen:
                    # Every requirement the event satisfies, not only the list it was sampled in.
                    seen[event.id] = EventMatch(event.id, plan_matches(plan, event))
        truncated = evidence.considered >= POOL or any(
            len(sir.events) >= PER_SIR for sir in evidence.sirs
        )
        return PlanMapMatches(plan, evidence.considered, truncated, tuple(seen.values()))
