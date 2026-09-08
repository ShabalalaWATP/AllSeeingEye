"""Live-session admission and release around bounded SEC document execution."""

import asyncio
from datetime import date
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.auth.current_session import validate_current_session
from ase.application.dto import AccessClaims
from ase.application.ports import (
    Clock,
    RateLimiter,
    RefreshTokenRepository,
    UnitOfWork,
    UserRepository,
)
from ase.application.ports.research_inputs import ResearchInputReceipt, ResearchInputStore
from ase.application.ports.sec_filings import SecFilingProvider, SecSelectionStore
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.errors import InvalidRequest, RateLimited, Unauthenticated
from ase.domain.sec_filings import SecFilingChoice, SecFilingPage
from ase.domain.users import User

REQUEST_SECONDS = 20


class SecFilings:
    def __init__(
        self,
        users: UserRepository,
        refresh: RefreshTokenRepository,
        access: AccessPolicy,
        clock: Clock,
        limiter: RateLimiter,
        uow: UnitOfWork,
        provider: SecFilingProvider,
        selections: SecSelectionStore,
        inputs: ResearchInputStore,
        admission: SourceAdmission,
    ) -> None:
        self.users, self.refresh, self.access, self.clock = users, refresh, access, clock
        self.limiter, self.uow, self.provider = limiter, uow, provider
        self.selections, self.inputs, self.admission = selections, inputs, admission

    async def _context(self, claims: AccessClaims) -> User:
        await self.users.lock_administration()
        actor = await validate_current_session(claims, self.users, self.refresh, self.clock)
        await self.access.context(actor)
        # Logout need not acquire the administration guard. Check its family
        # after all other awaited access work, immediately before private reads.
        return await validate_current_session(claims, self.users, self.refresh, self.clock)

    async def _enabled(self) -> None:
        if not await self.admission.enabled("research-sec-submissions"):
            raise InvalidRequest("SEC research is disabled by the administrator.")

    def _limit(self, claims: AccessClaims) -> None:
        retry = self.limiter.hit(f"sec-filings:{claims.user_id}", 20, 900)
        if retry is not None:
            raise RateLimited(retry)

    def _expiry(self, claims: AccessClaims) -> None:
        if claims.expires_at <= self.clock.now():
            raise Unauthenticated("The session has ended. Sign in again.")

    async def list(
        self, claims: AccessClaims, cik: str, since: date, until: date, page: int, offset: int
    ) -> tuple[SecFilingPage, tuple[SecFilingChoice, ...]]:
        if (
            not date(1994, 1, 1) <= since <= until <= self.clock.now().date()
            or (until - since).days > 3660
            or not 0 <= page <= 50
            or not 0 <= offset <= 9980
            or offset % 20
        ):
            raise InvalidRequest(
                "Choose filing dates from 1994 through today, at most ten years, and "
                "a bounded page."
            )
        try:
            await self._context(claims)
        finally:
            await self.uow.rollback()
        self._limit(claims)
        await self._enabled()
        try:
            async with asyncio.timeout(REQUEST_SECONDS):
                result = await self.provider.list(cik, since, until, page, offset)
        except TimeoutError:
            raise InvalidRequest("SEC listing timed out; no retry was made.") from None
        async with self.admission.guard():
            await self._enabled()
            try:
                await self._context(claims)
                self._expiry(claims)
                choices = self.selections.issue(claims, result)
            finally:
                await self.uow.rollback()
        self._expiry(claims)
        return result, choices

    async def import_filing(self, claims: AccessClaims, key: UUID) -> ResearchInputReceipt:
        reservation = None
        retained = False
        original_reserved = False
        try:
            try:
                actor = await self._context(claims)
                choice = self.selections.get(claims, key)
                self._limit(claims)
                self.selections.reserve_original(claims, key)
                original_reserved = True
                reservation = self.inputs.reserve(actor, choice.filing.primary_document)
            finally:
                await self.uow.rollback()
            await self._enabled()
            try:
                async with asyncio.timeout(REQUEST_SECONDS):
                    extraction, data = await self.provider.fetch(choice.filing)
            except TimeoutError:
                raise InvalidRequest("SEC filing retrieval timed out; no retry was made.") from None
            async with self.admission.guard():
                await self._enabled()
                try:
                    await self._context(claims)
                    self._expiry(claims)
                    self.selections.get(claims, key)
                    self.inputs.require_pending(reservation)
                    self.selections.put_original(claims, key, data)
                    receipt = self.inputs.put(reservation, extraction).receipt
                    retained = True
                finally:
                    await self.uow.rollback()
            self._expiry(claims)
            return receipt
        finally:
            if reservation is not None:
                self.inputs.release(reservation)
            if original_reserved and not retained:
                self.selections.release_original(key)

    async def original(self, claims: AccessClaims, key: UUID) -> tuple[str, bytes]:
        try:
            await self._context(claims)
            choice = self.selections.get(claims, key)
            data = self.selections.original(claims, key)
            self._expiry(claims)
        except BaseException:
            await self.uow.rollback()
            raise
        # Successful HTTP release retains the guard until the request session
        # closes; no awaited rollback may interleave a logout before delivery.
        return choice.filing.primary_document, data

    async def release_choices(
        self, claims: AccessClaims, choices: tuple[SecFilingChoice, ...]
    ) -> None:
        """Recheck after disconnect-task cleanup, immediately before private HTTP release."""
        try:
            await self._context(claims)
            for choice in choices:
                self.selections.get(claims, choice.selection_id)
            self._expiry(claims)
        except BaseException:
            await self.uow.rollback()
            raise

    async def release_input(
        self, claims: AccessClaims, key: UUID, input_id: UUID
    ) -> ResearchInputReceipt:
        try:
            actor = await self._context(claims)
            self.selections.get(claims, key)
            receipt = self.inputs.read(actor, input_id).receipt
            self._expiry(claims)
        except BaseException:
            await self.uow.rollback()
            raise
        return receipt
