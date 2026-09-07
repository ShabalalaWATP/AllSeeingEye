"""Admit one routed model call and retain reviewable claims against a frozen report."""

import asyncio
from dataclasses import dataclass
from typing import Literal
from uuid import UUID, uuid4

from ase.application.dto import AccessClaims, RequestContext
from ase.application.model_routing import ModelRouting
from ase.application.ports import Clock, UnitOfWork
from ase.application.ports.llm import LlmGateway, LlmUsageRepository, SecretCipher
from ase.application.ports.services import RateLimiter
from ase.application.reports.claim_proposal_model import claim_input_supported, propose_claims
from ase.application.reports.claims import ReportClaims
from ase.domain.claim_origin import ClaimModelOrigin
from ase.domain.claim_revisions import ClaimRevision
from ase.domain.errors import NoModelAvailable, RateLimited
from ase.domain.llm import LlmRole, LlmUsage


@dataclass(frozen=True, slots=True)
class ClaimGenerationResult:
    status: Literal["completed", "empty", "invalid", "unavailable", "unsupported"]
    items: tuple[ClaimRevision, ...] = ()


class GenerateClaims:
    def __init__(
        self,
        claims: ReportClaims,
        routing: ModelRouting,
        gateway: LlmGateway,
        cipher: SecretCipher,
        usage: LlmUsageRepository,
        clock: Clock,
        limiter: RateLimiter,
        uow: UnitOfWork,
    ) -> None:
        self.claims, self.routing, self.gateway = claims, routing, gateway
        self.cipher, self.usage, self.clock = cipher, usage, clock
        self.limiter, self.uow = limiter, uow

    async def execute(
        self, actor: AccessClaims, report_id: UUID, number: int, context: RequestContext
    ) -> ClaimGenerationResult:
        anchor = await self.claims.prepare_proposals(actor, report_id, number)
        if not claim_input_supported(anchor.version):
            return ClaimGenerationResult("unsupported")
        if not self.cipher.available:
            raise NoModelAvailable()
        routing = await self.routing.snapshot(team_id=anchor.team_id)
        profile = routing.required(LlmRole.ASSESSMENT)
        key = self.cipher.decrypt(profile.api_key_encrypted)
        # Routing reads can open another transaction after admission. Release it too.
        await self.uow.commit()
        for bucket, limit in (
            (f"claims:report:{report_id}:{number}", 2),
            (f"claims:user:{actor.user_id}", 6),
            ("claims:global", 30),
        ):
            retry = self.limiter.hit(bucket, limit, 3600)
            if retry is not None:
                raise RateLimited(retry)
        try:
            draft = await propose_claims(self.gateway, profile, key, anchor.version)
        except asyncio.CancelledError:
            # The provider may have incurred cost even when it returned no token counts.
            # Finish bounded accounting in this session, never detach a database task.
            async with asyncio.timeout(5):
                await self.usage.add(
                    LlmUsage(
                        at=self.clock.now(),
                        profile_id=profile.id,
                        user_id=actor.user_id,
                        purpose="claim_proposals",
                        ok=False,
                        latency_ms=0,
                        error="cancelled",
                    )
                )
                await self.uow.commit()
            raise
        # Operational cost records survive a later access revocation or quota failure.
        # They contain no report text, evidence, credentials or caller-provided errors.
        if draft.status != "unsupported":
            await self.usage.add(
                LlmUsage(
                    at=self.clock.now(),
                    profile_id=profile.id,
                    user_id=actor.user_id,
                    purpose="claim_proposals",
                    ok=draft.status in ("completed", "empty"),
                    latency_ms=draft.latency_ms,
                    prompt_tokens=draft.prompt_tokens,
                    completion_tokens=draft.completion_tokens,
                    error=None if draft.status in ("completed", "empty") else draft.status,
                )
            )
            await self.uow.commit()
        if draft.status != "completed" or draft.input_sha256 is None:
            await self.claims.prepare_proposals(actor, report_id, number)
            return ClaimGenerationResult(draft.status)
        origin = ClaimModelOrigin(
            uuid4(),
            profile.id,
            profile.revision,
            profile.provider,
            profile.model,
            draft.model,
            draft.input_sha256,
            draft.method_version,
            self.clock.now(),
        )
        revisions = await self.claims.persist_proposals(
            actor, anchor, draft.proposals, origin, context
        )
        return ClaimGenerationResult("completed", revisions)
