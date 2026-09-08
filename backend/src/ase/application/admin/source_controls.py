"""Administrator source activation and isolated bounded connectivity checks."""

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.feeds.health import HealthRegistry, SourceHealth
from ase.application.policy import require_admin
from ase.application.ports import (
    Clock,
    RateLimiter,
    RefreshTokenRepository,
    UnitOfWork,
    UserRepository,
)
from ase.application.ports.feed_release import GuardedFeedConnector
from ase.application.ports.feeds import FeedConnector
from ase.application.ports.source_controls import SourceAdmission, SourceControlRepository
from ase.domain.audit import AuditAction
from ase.domain.errors import InvalidRequest, NotFound, RateLimited, Unauthenticated
from ase.domain.source_controls import source_control_keys
from ase.domain.sources import SourceSpec


@dataclass(frozen=True, slots=True)
class ControlledSource:
    spec: SourceSpec
    health: SourceHealth
    enabled: bool
    test_available: bool
    environment_disabled: bool


@dataclass(frozen=True, slots=True)
class SourceTestResult:
    ok: bool
    fetched: int
    capped: bool
    message: str


class AdminSourceControls:
    def __init__(
        self,
        users: UserRepository,
        refresh: RefreshTokenRepository,
        controls: SourceControlRepository,
        admission: SourceAdmission,
        connectors: Sequence[FeedConnector],
        specs: Sequence[SourceSpec],
        health: HealthRegistry,
        resume: Callable[[str], None],
        clock: Clock,
        limiter: RateLimiter,
        auditor: Auditor,
        uow: UnitOfWork,
        disabled: tuple[str, ...] = (),
    ) -> None:
        self._users, self._refresh, self._controls = users, refresh, controls
        self._admission, self._health, self._resume = admission, health, resume
        self._clock, self._limiter, self._auditor, self._uow = clock, limiter, auditor, uow
        self._connectors = {connector.spec.id: connector for connector in connectors}
        self._specs = {spec.id: spec for spec in specs}
        self._specs.update({connector.spec.id: connector.spec for connector in connectors})
        self._disabled = frozenset(disabled)

    async def _guard(self, claims: AccessClaims) -> None:
        await self._users.lock_administration()
        await self._users.lock_by_id(claims.user_id)
        require_admin(
            await validate_current_session(claims, self._users, self._refresh, self._clock)
        )

    def _spec(self, source_id: str) -> SourceSpec:
        spec = self._specs.get(source_id)
        if spec is None:
            raise NotFound()
        return spec

    async def list(self, claims: AccessClaims) -> list[ControlledSource]:
        await self._guard(claims)
        await self._uow.commit()
        enabled = await self._admission.enabled_many(tuple(self._specs))
        result = [
            ControlledSource(
                spec,
                self._health.get(spec.id),
                enabled[spec.id],
                spec.id in self._connectors,
                any(key in self._disabled for key in source_control_keys(spec.id)),
            )
            for spec in sorted(
                self._specs.values(), key=lambda spec: (spec.name.casefold(), spec.id)
            )
        ]
        await self._guard(claims)
        await self._uow.commit()
        return result

    async def activate(
        self, claims: AccessClaims, source_id: str, enabled: bool, context: RequestContext
    ) -> None:
        # Lock order is release guard, then administrative/account locks. A source
        # cannot be disabled between a final admission read and its publication.
        async with self._admission.guard():
            await self._activate(claims, source_id, enabled, context)

    async def _activate(
        self, claims: AccessClaims, source_id: str, enabled: bool, context: RequestContext
    ) -> None:
        self._spec(source_id)
        await self._guard(claims)
        keys = source_control_keys(source_id)
        if enabled and any(key in self._disabled for key in keys):
            raise InvalidRequest(
                "This source is disabled in the operator environment configuration."
            )
        overrides = await self._controls.all()
        if enabled and any(not overrides.get(parent, True) for parent in keys[1:]):
            raise InvalidRequest(
                "Enable this source's parent source before enabling its research variant."
            )
        await self._controls.set(source_id, enabled, self._clock.now(), claims.user_id)
        await self._auditor.record(
            AuditAction.SOURCE_ACTIVATION_CHANGED,
            actor=claims.user_id,
            subject=source_id,
            ip=context.ip,
            details={"enabled": enabled},
        )
        await self._uow.commit()

    async def reset(
        self, claims: AccessClaims, source_id: str, context: RequestContext
    ) -> SourceHealth:
        self._spec(source_id)
        if source_id not in self._connectors:
            raise InvalidRequest("On-demand sources have no live polling circuit to reset.")
        await self._guard(claims)
        self._resume(source_id)
        await self._auditor.record(
            AuditAction.SOURCE_RESET, actor=claims.user_id, subject=source_id, ip=context.ip
        )
        await self._uow.commit()
        return self._health.get(source_id)

    async def test(
        self, claims: AccessClaims, source_id: str, context: RequestContext
    ) -> SourceTestResult:
        self._spec(source_id)
        await self._guard(claims)
        connector = self._connectors.get(source_id)
        if connector is None:
            raise InvalidRequest("This on-demand source requires a scoped research query to test.")
        for key in (f"source-test:user:{claims.user_id}", f"source-test:source:{source_id}"):
            retry = self._limiter.hit(key, 3, 60)
            if retry is not None:
                raise RateLimited(retry)
        await self._uow.commit()
        generation: int | None = None
        try:
            async with asyncio.timeout(20):
                if isinstance(connector, GuardedFeedConnector):
                    generation = await connector.current_generation()
                    batch = await connector.fetch_batch()
                    events, generation = batch.events, batch.generation
                else:
                    events = await connector.fetch()
            result = SourceTestResult(
                True,
                min(len(events), 1000),
                len(events) > 1000,
                "Source responded. Test records were not published or saved.",
            )
        except TimeoutError:
            result = SourceTestResult(
                False, 0, False, "The source exceeded the 20-second test deadline."
            )
        except Exception:
            result = SourceTestResult(
                False,
                0,
                False,
                "The source could not be fetched. No upstream error details are exposed.",
            )
        await self._guard(claims)
        await self._auditor.record(
            AuditAction.SOURCE_TESTED,
            actor=claims.user_id,
            subject=source_id,
            ip=context.ip,
            details={"ok": result.ok, "fetched": result.fetched},
        )
        await self._uow.commit()
        if isinstance(connector, GuardedFeedConnector) and generation is not None:
            async with self._admission.guard(), connector.release_guard(generation) as current:
                if not current:
                    result = SourceTestResult(
                        False,
                        0,
                        False,
                        "The source connection changed during the test. Test it again.",
                    )
        # Guard cleanup itself awaits database commit/close. Validate private result
        # authority after that cleanup, then check expiry synchronously before return.
        require_admin(
            await validate_current_session(claims, self._users, self._refresh, self._clock)
        )
        if claims.expires_at <= self._clock.now():
            raise Unauthenticated()
        return result
