"""One consented vision call against the destination's frozen model configuration."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.ai_usage import AiUsageAccounting
from ase.application.model_routing import ModelRouting
from ase.application.ports import Clock, RateLimiter, UnitOfWork
from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.ports.research_inputs import (
    INPUT_TTL_SECONDS,
    InputExtraction,
    ResearchInputReceipt,
    ResearchInputStore,
)
from ase.application.research.photo_evidence import LIMITATIONS, photo_events
from ase.application.research.photo_inputs import (
    image_provenance,
    photo_ids,
    photo_messages,
    read_photos,
)
from ase.application.research.photo_model import (
    SYSTEM_PROMPT,
    PhotoVision,
    SessionCheck,
    UsageRecorder,
    photo_assessment_schema,
)
from ase.application.research.photo_sun import sun_checks
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.llm import LlmMessage, LlmRequest, LlmRole
from ase.domain.photo_geolocation import PhotoAssessment, PhotoProvenance, SunShadowCheck
from ase.domain.users import User


@dataclass(frozen=True, slots=True)
class PhotoResult:
    assessment: PhotoAssessment
    provenance: PhotoProvenance
    receipt: ResearchInputReceipt
    sun_checks: tuple[SunShadowCheck, ...] = ()


class PhotoGeolocation:
    def __init__(
        self,
        access: AccessPolicy,
        routing: ModelRouting,
        store: ResearchInputStore,
        gateway: LlmGateway,
        cipher: SecretCipher,
        clock: Clock,
        limiter: RateLimiter,
        uow: UnitOfWork,
        admission: asyncio.Semaphore,
        record_usage: UsageRecorder,
        ai_usage: AiUsageAccounting | None = None,
    ) -> None:
        self._access, self._routing, self._store = access, routing, store
        self._clock = clock
        self._vision = PhotoVision(gateway, cipher, clock, record_usage, ai_usage)
        self._limiter, self._uow, self._admission = limiter, uow, admission

    def _require_capacity(self, actor: User, ids: tuple[UUID, ...]) -> None:
        for key, limit in (
            (f"photo-geolocation:user:{actor.id}", 3),
            *((f"photo-geolocation:input:{input_id}", 2) for input_id in ids),
        ):
            retry = self._limiter.hit(key, limit, INPUT_TTL_SECONDS)
            if retry is not None:
                raise RateLimited(retry)
        if self._admission.locked():
            raise RateLimited(30)

    async def execute(
        self,
        actor: User,
        input_id: UUID,
        *,
        consent_to_send_image: bool,
        additional_input_ids: tuple[UUID, ...] = (),
        question: str = "Where might this photograph have been taken?",
        hints: str = "",
        team_id: UUID | None = None,
        captured_at: datetime | None = None,
        check_session: SessionCheck,
    ) -> PhotoResult:
        if consent_to_send_image is not True:
            raise InvalidRequest("Consent is required before sending a sanitised image to AI.")
        if len(question) > 2000 or len(hints) > 1000:
            raise InvalidRequest("The photo question or location hints exceed the text limit.")
        if captured_at is not None and captured_at.utcoffset() is None:
            raise InvalidRequest("The capture time must state its UTC offset.")
        ids = photo_ids(input_id, additional_input_ids)
        try:
            current = await self._access.context(actor)
            current.require_create(team_id)
            await check_session()
            originals = read_photos(self._store, current.actor, ids)
            original = originals[0]
            routing = await self._routing.snapshot(team_id=team_id, personal_owner_id=actor.id)
            profile = routing.required(LlmRole.ASSESSMENT)
        finally:
            await self._uow.rollback()
        self._require_capacity(actor, ids)
        async with self._admission:
            reservation = self._store.reserve(current.actor, original.receipt.filename)
            try:
                # No database transaction or account guard crosses the outbound call.
                request = LlmRequest(
                    messages=(
                        LlmMessage("system", SYSTEM_PROMPT),
                        *photo_messages(originals, question, hints),
                    ),
                    max_output_tokens=profile.token_budget(4000),
                    temperature=profile.temperature,
                    reasoning_effort=profile.reasoning_effort,
                    provider=profile.provider,
                    profile_id=profile.id,
                    json_schema=photo_assessment_schema(),
                    schema_name="photo_geolocation",
                )

                async def before_send() -> None:
                    try:
                        ready = await self._access.context(actor)
                        ready.require_create(team_id)
                        await check_session()
                        read_photos(self._store, ready.actor, ids)
                    finally:
                        await self._uow.rollback()

                assessment, result = await self._vision.analyse(
                    actor.id,
                    profile,
                    request,
                    before_send,
                    photo_ids=tuple(f"photo-{index}" for index in range(1, len(ids) + 1)),
                    team_id=team_id,
                )
                provenance = PhotoProvenance(
                    profile_id=profile.id,
                    profile_revision=profile.revision,
                    provider=profile.provider,
                    configured_model=profile.model,
                    returned_model=result.model,
                    analysed_at=self._clock.now(),
                    original_sha256=original.receipt.sha256,
                    image_sha256=original.frames[0].sha256,
                    photos=image_provenance(originals),
                )
                try:
                    current = await self._access.context(actor, for_update=True)
                    current.require_create(team_id)
                    await check_session()
                    read_photos(self._store, current.actor, ids)
                    # Raw bytes remain only on the original expiring receipt. Derived report
                    # evidence contains labelled hypotheses and hashes, no image payload.
                    extraction = InputExtraction(
                        original.receipt.filename,
                        original.receipt.media_type,
                        original.receipt.sha256,
                        photo_events(assessment, provenance),
                        LIMITATIONS,
                        parent_input_id=input_id,
                        parent_input_ids=ids,
                    )
                    receipt = self._store.put(reservation, extraction).receipt
                    return PhotoResult(
                        assessment, provenance, receipt, tuple(sun_checks(assessment, captured_at))
                    )
                finally:
                    await self._uow.rollback()
            finally:
                self._store.release(reservation)
