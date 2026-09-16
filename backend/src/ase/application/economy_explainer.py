"""Cadence, admission and honest states for the plain-English economy explainer.

One model call per fact-pack fingerprint, and never more often than once a day. The
cached text is served to everyone and is marked stale as soon as the figures move on.
Nothing that fails the mechanical checks is stored, and no prompt is ever kept.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable

from ase.application.economy_explainer_facts import SOURCE_LABELS, FactPack, fingerprint
from ase.application.economy_explainer_model import (
    REASONS,
    ExplainerGenerator,
    GenerationOutcome,
)
from ase.application.model_routing import ModelRouting
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.economy_explainer import EconomyExplainerRepository
from ase.domain.economy_explainer import (
    REGENERATION_INTERVAL,
    ExplainerStatus,
    ExplainerView,
    StoredExplainer,
    window_start,
)
from ase.domain.errors import NoModelAvailable
from ase.domain.llm import LlmRole

log = logging.getLogger(__name__)
FactSource = Callable[[], Awaitable[FactPack]]
NOTHING_YET = (
    "No plain-English summary has been written yet. One is written from the figures on "
    "this page at most once a day."
)
BUSY = "A fresh plain-English summary is being written from the current figures."


class EconomyExplainerService:
    """Reads are cheap; only an eligible read or an administrator refresh may generate."""

    def __init__(
        self,
        repository: EconomyExplainerRepository,
        uow: UnitOfWork,
        routing: ModelRouting,
        generator: ExplainerGenerator,
        facts: FactSource,
        clock: Clock,
        admission: asyncio.Lock,
    ) -> None:
        self._repository, self._uow, self._routing = repository, uow, routing
        self._generator, self._facts, self._clock = generator, facts, clock
        self._admission = admission

    async def read(self, *, allow_generation: bool = True) -> ExplainerView:
        pack = await self._facts()
        finger = fingerprint(pack)
        latest = await self._load()
        if latest is not None and latest.fingerprint == finger:
            return _ready(latest)
        if not allow_generation or not self._due(latest):
            return _cached(latest)
        if self._admission.locked():
            return _cached(latest, status="generating", reason=BUSY)
        return await self._generate(pack, finger, latest)

    async def refresh(self) -> ExplainerView:
        """An administrator forces one regeneration, ignoring the daily cadence."""
        pack = await self._facts()
        finger = fingerprint(pack)
        latest = await self._load()
        if self._admission.locked():
            return _cached(latest, status="generating", reason=BUSY)
        return await self._generate(pack, finger, latest)

    async def _load(self) -> StoredExplainer | None:
        latest = await self._repository.latest()
        # Release the read transaction before any model work begins.
        await self._uow.commit()
        return latest

    def _due(self, latest: StoredExplainer | None) -> bool:
        if latest is None:
            return True
        return self._clock.now() - latest.generated_at >= REGENERATION_INTERVAL

    async def _generate(
        self, pack: FactPack, finger: str, previous: StoredExplainer | None
    ) -> ExplainerView:
        async with self._admission:
            # Another request may have generated while this one waited for the guard.
            latest = await self._load()
            if latest is not None and latest.fingerprint == finger:
                return _ready(latest)
            try:
                profiles = await self._routing.snapshot(role=LlmRole.ASSESSMENT)
                profile = profiles.required(LlmRole.ASSESSMENT)
            except NoModelAvailable:
                return _failed(latest or previous, "model_unavailable")
            outcome = await self._generator.generate(profile, pack)
            if outcome.text is None:
                if outcome.failure == "validation_failed":
                    log.warning(
                        "economy_explainer.validation_failed",
                        extra={"attempts": outcome.attempts, "problems": len(outcome.problems)},
                    )
                return _failed(latest or previous, outcome.failure or "model_failed", outcome)
            now = self._clock.now()
            stored = StoredExplainer(
                fingerprint=finger,
                window_start=window_start(now),
                text=outcome.text,
                model=outcome.model[:255] or profile.model[:255],
                generated_at=now,
                snapshot_fetched_at=pack.fetched_at,
                prompt_tokens=outcome.prompt_tokens,
                completion_tokens=outcome.completion_tokens,
            )
            try:
                await self._repository.save(stored)
                await self._uow.commit()
            except Exception:
                await self._uow.rollback()
                raise
            return _ready(stored)


def _ready(stored: StoredExplainer) -> ExplainerView:
    return ExplainerView("ready", False, stored, None, SOURCE_LABELS)


def _cached(
    latest: StoredExplainer | None,
    *,
    status: ExplainerStatus | None = None,
    reason: str | None = None,
) -> ExplainerView:
    if latest is None:
        return ExplainerView(status or "empty", False, None, reason or NOTHING_YET, SOURCE_LABELS)
    return ExplainerView(status or "stale", True, latest, reason, SOURCE_LABELS)


def _failed(
    latest: StoredExplainer | None, failure: str, outcome: GenerationOutcome | None = None
) -> ExplainerView:
    reason = (outcome.reason if outcome else None) or REASONS[failure]
    status: ExplainerStatus = (
        "validation_failed" if failure == "validation_failed" else "unavailable"
    )
    return ExplainerView(status, latest is not None, latest, reason, SOURCE_LABELS)
