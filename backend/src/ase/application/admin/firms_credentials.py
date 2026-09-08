"""Administrator draft/test/confirm with no plaintext readback or locks across NASA I/O."""

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from ase.application.auditing import Auditor
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims, RequestContext
from ase.application.policy import require_admin
from ase.application.ports import (
    Clock,
    RateLimiter,
    RefreshTokenRepository,
    UnitOfWork,
    UserRepository,
)
from ase.application.ports.firms_credentials import FirmsCredentialRepository, FirmsProbe
from ase.application.ports.llm import SecretCipher
from ase.domain.audit import AuditAction
from ase.domain.errors import Conflict, InvalidRequest, RateLimited, Unauthenticated
from ase.domain.firms_credentials import FirmsCredential

TTL = timedelta(minutes=15)


@dataclass(frozen=True, slots=True)
class FirmsConnectionStatus:
    revision: int
    active_revision: int
    configured: bool
    credential_origin: Literal["environment", "database", "none"]
    environment_disabled: bool
    encryption_available: bool
    area: str
    draft_present: bool
    draft_expires_at: datetime | None
    tested_at: datetime | None
    test_generation: int
    test_ok: bool


@dataclass(frozen=True, slots=True)
class FirmsTestResult:
    status: FirmsConnectionStatus
    ok: bool
    fetched: int
    message: str


class AdminFirmsCredentials:
    def __init__(
        self,
        users: UserRepository,
        refresh: RefreshTokenRepository,
        repository: FirmsCredentialRepository,
        cipher: SecretCipher,
        probe: FirmsProbe,
        clock: Clock,
        limiter: RateLimiter,
        auditor: Auditor,
        uow: UnitOfWork,
        resume: Callable[[], None],
        *,
        area: str,
        environment_managed: bool,
        environment_disabled: bool,
    ) -> None:
        self.users, self.refresh, self.repository = users, refresh, repository
        self.cipher, self.probe, self.clock = cipher, probe, clock
        self.limiter, self.auditor, self.uow, self.resume = limiter, auditor, uow, resume
        self.area, self.environment_managed, self.environment_disabled = (
            area,
            environment_managed,
            environment_disabled,
        )

    async def guard(self, claims: AccessClaims) -> None:
        await self.users.lock_administration()
        await self.users.lock_by_id(claims.user_id)
        require_admin(await validate_current_session(claims, self.users, self.refresh, self.clock))

    async def finish(self, claims: AccessClaims) -> None:
        # Preparation/auditing can yield after admission. Recheck immediately before
        # commit, then recheck the current session before releasing private metadata.
        require_admin(await validate_current_session(claims, self.users, self.refresh, self.clock))
        await self.uow.commit()
        await self.guard(claims)
        if claims.expires_at <= self.clock.now():
            raise Unauthenticated("The session has ended. Sign in again.")

    def status(self, row: FirmsCredential, claims: AccessClaims) -> FirmsConnectionStatus:
        valid = row.draft_valid(self.clock.now(), self.area)
        tested = bool(
            valid
            and row.tested_at
            and row.tested_at + TTL > self.clock.now()
            and row.tested_revision == row.revision
            and row.tested_actor == claims.user_id
            and row.tested_family == claims.family_id
            and row.tested_security_version == claims.security_version
        )
        origin: Literal["environment", "database", "none"] = (
            "environment"
            if self.environment_managed
            else "database"
            if row.active_encrypted
            else "none"
        )
        return FirmsConnectionStatus(
            row.revision,
            row.active_revision,
            origin != "none",
            origin,
            self.environment_disabled,
            self.cipher.available,
            self.area,
            valid,
            row.draft_expires_at if valid else None,
            row.tested_at if tested else None,
            row.test_generation,
            tested,
        )

    async def get(self, claims: AccessClaims) -> FirmsConnectionStatus:
        await self.guard(claims)
        # Environment credentials are independent of encrypted database storage.
        # Do not require its newer table to inspect a read-only operator connection.
        row = FirmsCredential() if self.environment_managed else await self.repository.get()
        result = self.status(row, claims)
        await self.finish(claims)
        return result

    async def editable(self, claims: AccessClaims, expected: int) -> FirmsCredential:
        await self.guard(claims)
        if self.environment_managed:
            raise InvalidRequest("FIRMS credentials are managed by the operator environment.")
        row = await self.repository.get()
        if row.revision != expected:
            raise Conflict("The FIRMS connection changed. Reload its current status.")
        return row

    async def record(
        self, claims: AccessClaims, context: RequestContext, action: AuditAction
    ) -> None:
        await self.auditor.record(
            action, actor=claims.user_id, subject="firms_viirs_noaa20", ip=context.ip
        )

    async def draft(
        self, claims: AccessClaims, key: str, expected: int, context: RequestContext
    ) -> FirmsConnectionStatus:
        row = await self.editable(claims, expected)
        if not self.cipher.available:
            raise InvalidRequest("Configure server encryption before storing a FIRMS key.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{16,128}", key):
            raise InvalidRequest("Invalid FIRMS map key format.")
        row.draft_encrypted = self.cipher.encrypt(key)
        row.revision += 1
        row.draft_area, row.draft_expires_at = self.area, self.clock.now() + TTL
        row.tested_at = row.tested_revision = None
        await self.repository.save(row)
        await self.record(claims, context, AuditAction.FIRMS_DRAFT_SAVED)
        await self.finish(claims)
        return self.status(row, claims)

    async def test(
        self, claims: AccessClaims, expected: int, context: RequestContext
    ) -> FirmsTestResult:
        row = await self.editable(claims, expected)
        if self.environment_disabled:
            raise InvalidRequest("FIRMS is disabled by the operator environment.")
        if not row.draft_valid(self.clock.now(), self.area) or not self.cipher.available:
            raise InvalidRequest("Save a fresh FIRMS draft before testing.")
        for key in (f"firms-test:{claims.user_id}", "firms-test:global"):
            retry = self.limiter.hit(key, 3, 60)
            if retry is not None:
                raise RateLimited(retry)
        row.test_generation += 1
        generation = row.test_generation
        row.tested_at = row.tested_revision = None
        await self.repository.save(row)
        await self.record(claims, context, AuditAction.FIRMS_TEST_STARTED)
        require_admin(await validate_current_session(claims, self.users, self.refresh, self.clock))
        await self.uow.commit()
        ok, fetched = False, 0
        try:
            async with asyncio.timeout(20):
                if row.draft_encrypted is None:
                    raise InvalidRequest("Save a fresh FIRMS draft before testing.")
                fetched = await self.probe.test(self.cipher.decrypt(row.draft_encrypted), self.area)
            ok = True
        except Exception:
            ok = False  # Never expose upstream/decryption errors or secret-bearing URLs.
        current = await self.editable(claims, expected)
        if current.test_generation != generation or not current.draft_valid(
            self.clock.now(), self.area
        ):
            raise Conflict("The FIRMS draft or test changed. Test the current draft again.")
        if ok:
            current.tested_at, current.tested_revision = self.clock.now(), expected
            current.tested_actor, current.tested_family = claims.user_id, claims.family_id
            current.tested_security_version = claims.security_version
        await self.repository.save(current)
        await self.record(claims, context, AuditAction.FIRMS_TESTED)
        await self.finish(claims)
        return FirmsTestResult(
            self.status(current, claims),
            ok,
            min(max(fetched, 0), 30000) if ok else 0,
            "FIRMS responded. Test records were not published or saved."
            if ok
            else "FIRMS could not be tested. Check the key and configured area, then retry.",
        )

    async def confirm(
        self, claims: AccessClaims, expected: int, generation: int, context: RequestContext
    ) -> FirmsConnectionStatus:
        row = await self.editable(claims, expected)
        if self.environment_disabled:
            raise InvalidRequest("FIRMS is disabled by the operator environment.")
        if not self.status(row, claims).test_ok or row.test_generation != generation:
            raise Conflict("A successful current FIRMS test is required before activation.")
        row.active_encrypted, row.draft_encrypted = row.draft_encrypted, None
        row.active_revision += 1
        row.revision += 1
        row.draft_expires_at = row.tested_at = row.tested_revision = None
        row.draft_area = None
        await self.repository.save(row)
        await self.record(claims, context, AuditAction.FIRMS_CONFIRMED)
        await self.finish(claims)
        self.resume()
        return self.status(row, claims)

    async def clear(
        self, claims: AccessClaims, expected: int, context: RequestContext
    ) -> FirmsConnectionStatus:
        row = await self.editable(claims, expected)
        row.active_encrypted = row.draft_encrypted = None
        row.revision += 1
        row.active_revision += 1
        row.draft_expires_at = row.tested_at = row.tested_revision = None
        row.draft_area = None
        await self.repository.save(row)
        await self.record(claims, context, AuditAction.FIRMS_CLEARED)
        await self.finish(claims)
        return self.status(row, claims)
