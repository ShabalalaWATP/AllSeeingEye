"""One consented vision call against the destination's frozen model configuration."""

import asyncio
import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from ase.application.access import AccessPolicy
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
from ase.application.research.photo_model import (
    SYSTEM_PROMPT,
    PhotoVision,
    SessionCheck,
    UsageRecorder,
)
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.llm import LlmImage, LlmMessage, LlmRequest, LlmRole
from ase.domain.photo_geolocation import PhotoAssessment, PhotoProvenance
from ase.domain.users import User


@dataclass(frozen=True, slots=True)
class PhotoResult:
    assessment: PhotoAssessment
    provenance: PhotoProvenance
    receipt: ResearchInputReceipt


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
    ) -> None:
        self._access, self._routing, self._store = access, routing, store
        self._clock = clock
        self._vision = PhotoVision(gateway, cipher, clock, record_usage)
        self._limiter, self._uow, self._admission = limiter, uow, admission

    def _require_capacity(self, actor: User, input_id: UUID) -> None:
        for key, limit in (
            (f"photo-geolocation:user:{actor.id}", 3),
            (f"photo-geolocation:input:{input_id}", 2),
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
        question: str = "Where might this photograph have been taken?",
        hints: str = "",
        team_id: UUID | None = None,
        check_session: SessionCheck,
    ) -> PhotoResult:
        if consent_to_send_image is not True:
            raise InvalidRequest("Consent is required before sending a sanitised image to AI.")
        if len(question) > 2000 or len(hints) > 1000:
            raise InvalidRequest("The photo question or location hints exceed the text limit.")
        try:
            current = await self._access.context(actor)
            current.require_create(team_id)
            await check_session()
            original = self._store.read(current.actor, input_id)
            if (
                not original.receipt.media_type.startswith("image/")
                or len(original.frames) != 1
                or original.receipt.parent_input_id is not None
            ):
                raise InvalidRequest("Upload one original photograph for visual geolocation.")
            frame = original.frames[0]
            if hashlib.sha256(frame.png).hexdigest() != frame.sha256:
                raise InvalidRequest("The sanitised image digest does not match its receipt.")
            routing = await self._routing.snapshot(team_id=team_id, personal_owner_id=actor.id)
            profile = routing.required(LlmRole.ASSESSMENT)
        finally:
            await self._uow.rollback()
        self._require_capacity(actor, input_id)
        async with self._admission:
            reservation = self._store.reserve(current.actor, original.receipt.filename)
            try:
                # No database transaction or account guard crosses the outbound call.
                request = LlmRequest(
                    messages=(
                        LlmMessage("system", SYSTEM_PROMPT),
                        LlmMessage(
                            "user",
                            json.dumps({"question": question, "unverified_hints": hints}),
                            images=(LlmImage(frame.png),),
                        ),
                    ),
                    max_output_tokens=profile.token_budget(4000),
                    temperature=profile.temperature,
                    reasoning_effort=profile.reasoning_effort,
                    provider=profile.provider,
                    profile_id=profile.id,
                    json_schema=PhotoAssessment.model_json_schema(),
                    schema_name="photo_geolocation",
                )

                async def before_send() -> None:
                    try:
                        ready = await self._access.context(actor)
                        ready.require_create(team_id)
                        await check_session()
                        self._store.read(ready.actor, input_id)
                    finally:
                        await self._uow.rollback()

                assessment, result = await self._vision.analyse(
                    actor.id,
                    profile,
                    request,
                    before_send,
                )
                provenance = PhotoProvenance(
                    profile_id=profile.id,
                    profile_revision=profile.revision,
                    provider=profile.provider,
                    configured_model=profile.model,
                    returned_model=result.model,
                    analysed_at=self._clock.now(),
                    original_sha256=original.receipt.sha256,
                    image_sha256=frame.sha256,
                )
                try:
                    current = await self._access.context(actor, for_update=True)
                    current.require_create(team_id)
                    await check_session()
                    original = self._store.read(current.actor, input_id)
                    # Raw bytes remain only on the original expiring receipt. Derived report
                    # evidence contains labelled hypotheses and hashes, no image payload.
                    extraction = InputExtraction(
                        original.receipt.filename,
                        original.receipt.media_type,
                        original.receipt.sha256,
                        photo_events(assessment, provenance),
                        LIMITATIONS,
                        parent_input_id=input_id,
                    )
                    receipt = self._store.put(reservation, extraction).receipt
                    return PhotoResult(assessment, provenance, receipt)
                finally:
                    await self._uow.rollback()
            finally:
                self._store.release(reservation)
