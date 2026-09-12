"""Authenticate, admit and recheck an upload around isolated extraction."""

from collections.abc import Awaitable, Callable
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.ports import Clock, RateLimiter, UnitOfWork
from ase.application.ports.research_inputs import (
    INPUT_TTL_SECONDS,
    MAX_INPUT_BYTES,
    DocumentImportPort,
    InputExtraction,
    InputPreviewFrame,
    InputReservation,
    ResearchInputReceipt,
    ResearchInputStore,
    StoredResearchInput,
)
from ase.domain.errors import InvalidRequest, RateLimited, Unauthenticated
from ase.domain.input_declarations import InputPassageDeclaration, apply_declarations
from ase.domain.users import User

# One six-photo set plus a replacement/retry round, still shared with other private uploads.
INPUT_ATTEMPTS_PER_WINDOW = 12
BeforeRetain = Callable[[], Awaitable[None]]


class ImportResearchInput:
    def __init__(
        self,
        access: AccessPolicy,
        runner: DocumentImportPort,
        store: ResearchInputStore,
        clock: Clock,
        limiter: RateLimiter,
        uow: UnitOfWork,
    ) -> None:
        self._access, self._runner, self._store = access, runner, store
        self._clock, self._limiter, self._uow = clock, limiter, uow

    async def reserve(self, actor: User, filename: str) -> InputReservation:
        """Admission precedes HTTP body reads, so slow uploads also occupy bounded slots."""
        try:
            current = await self._access.context(actor)
        finally:
            await self._uow.rollback()
        retry = self._limiter.hit(
            f"research-input:{actor.id}", INPUT_ATTEMPTS_PER_WINDOW, INPUT_TTL_SECONDS
        )
        if retry is not None:
            raise RateLimited(retry)
        if (
            not filename.strip()
            or len(filename) > 120
            or any(ord(char) < 32 or ord(char) == 127 for char in filename)
            or any(char in filename for char in "/\\:")
        ):
            raise InvalidRequest("Use a plain filename of at most 120 characters.")
        return self._store.reserve(current.actor, filename)

    def release(self, reservation: InputReservation) -> None:
        self._store.release(reservation)

    def previews(self, actor: User, input_id: UUID) -> tuple[InputPreviewFrame, ...]:
        return self._store.read(actor, input_id).frames

    async def discard(
        self,
        actor: User,
        input_id: UUID,
        *,
        before_discard: BeforeRetain,
    ) -> None:
        try:
            current = await self._access.context(actor, for_update=True)
            await before_discard()
            self._store.discard(current.actor, input_id)
        finally:
            await self._uow.rollback()

    async def declaration_targets(
        self,
        actor: User,
        input_id: UUID,
        *,
        before_release: BeforeRetain | None = None,
    ) -> StoredResearchInput:
        # Read all asynchronous authority before the final synchronous private-store read.
        # Successful release holds the guard until the request session is closed.
        await self._uow.rollback()
        try:
            current = await self._access.context(actor, for_update=True)
            if before_release is not None:
                await before_release()
            return self._store.read(current.actor, input_id)
        except BaseException:
            await self._uow.rollback()
            raise

    async def declare(
        self,
        actor: User,
        input_id: UUID,
        sha256: str,
        declarations: tuple[InputPassageDeclaration, ...],
        *,
        before_retain: BeforeRetain | None = None,
    ) -> ResearchInputReceipt:
        original = await self.declaration_targets(actor, input_id)
        if original.receipt.parent_input_id is not None:
            raise InvalidRequest("Declare against the original input, not a derived receipt.")
        reservation = await self.reserve(actor, original.receipt.filename)
        try:
            try:
                current = await self._access.context(actor, for_update=True)
                if before_retain is not None:
                    await before_retain()
                original = self._store.read(current.actor, input_id)
                if original.receipt.sha256 != sha256:
                    raise InvalidRequest("The input content digest does not match.")
                try:
                    events = apply_declarations(original.events, declarations, actor.id)
                except ValueError as exc:
                    raise InvalidRequest(str(exc)) from None
                extraction = InputExtraction(
                    original.receipt.filename,
                    original.receipt.media_type,
                    original.receipt.sha256,
                    events,
                    original.receipt.limitations,
                    original.frames,
                    parent_input_id=input_id,
                )
                return self._store.put(reservation, extraction).receipt
            finally:
                await self._uow.rollback()
        finally:
            self._store.release(reservation)

    async def execute(
        self, actor: User, filename: str, data: bytes, *, before_retain: BeforeRetain | None = None
    ) -> ResearchInputReceipt:
        reservation = await self.reserve(actor, filename)
        return await self.execute_reserved(actor, reservation, data, before_retain=before_retain)

    async def execute_reserved(
        self,
        actor: User,
        reservation: InputReservation,
        data: bytes,
        *,
        before_retain: BeforeRetain | None = None,
    ) -> ResearchInputReceipt:
        try:
            if (
                not actor.is_active
                or actor.id != reservation.owner_id
                or actor.security_version != reservation.security_version
            ):
                raise Unauthenticated()
            if not data or len(data) > MAX_INPUT_BYTES:
                raise InvalidRequest("Upload is empty or exceeds the 8 MiB size limit.")
            self._store.require_pending(reservation)
            try:
                # Streaming can take time. Recheck immediately before parser work.
                await self._access.context(actor)
            finally:
                await self._uow.rollback()
            extraction = await self._runner.extract(data, reservation.filename, self._clock.now())
            del data
            try:
                # Serialise the final identity check with account changes, after
                # the parser has finished and released all external resources.
                await self._access.context(actor, for_update=True)
                if before_retain is not None:
                    # The original request session can end while extraction runs.
                    # Keep this after the awaited guard, directly before the put.
                    await before_retain()
                result = self._store.put(reservation, extraction)
            finally:
                await self._uow.rollback()
            return result.receipt
        finally:
            self._store.release(reservation)
