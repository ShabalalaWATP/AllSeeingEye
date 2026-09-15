"""Prepare automatic proposals before report persistence acquires write guards."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from ase.application.ports import Clock, RateLimiter
from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.reports.claim_batch import build_proposal_batch, claim_body_digest
from ase.application.reports.claim_proposal_model import claim_input_supported, propose_claims
from ase.application.research.map_view_evidence import evidence_digest
from ase.domain.claim_generation import ClaimGenerationReceipt, ClaimGenerationStatus
from ase.domain.claim_origin import ClaimModelOrigin
from ase.domain.claim_revisions import ClaimRevision
from ase.domain.llm import LlmProfile, LlmRole, LlmUsage
from ase.domain.report_records import ReportVersion


@dataclass(frozen=True, slots=True)
class PendingAutomaticClaims:
    """Transient payload, never stored wholesale in report JSON or sent to clients."""

    report_id: UUID
    version_id: UUID
    actor_id: UUID
    evidence_sha256: str
    body_sha256: str
    receipt: ClaimGenerationReceipt
    revisions: tuple[ClaimRevision, ...] = ()
    usage: LlmUsage | None = None


class AutomaticClaims:
    def __init__(
        self, gateway: LlmGateway, cipher: SecretCipher, clock: Clock, limiter: RateLimiter
    ) -> None:
        self.gateway, self.cipher, self.clock, self.limiter = gateway, cipher, clock, limiter

    async def prepare(
        self,
        version: ReportVersion,
        actor_id: UUID,
        profile_for: Callable[[LlmRole], Awaitable[LlmProfile | None]],
        *,
        gateway: LlmGateway | None = None,
    ) -> PendingAutomaticClaims:
        """No repository writes: caller buffers usage until final report authorisation.

        The caller must have ended all read transactions before entering this stage.
        Frozen RoleProfiles prevent an administrator's concurrent reassignment from
        switching providers halfway through the report pipeline.
        """
        anchor = PendingAutomaticClaims(
            version.report_id,
            version.id,
            actor_id,
            evidence_digest(version),
            claim_body_digest(version),
            ClaimGenerationReceipt(ClaimGenerationStatus.NO_MODEL),
        )
        profile = await profile_for(LlmRole.ASSESSMENT)
        if not claim_input_supported(version):
            return self._outcome(anchor, ClaimGenerationReceipt(ClaimGenerationStatus.UNSUPPORTED))
        if profile is None or not self.cipher.available:
            return anchor
        for bucket, limit in ((f"claims:user:{actor_id}", 6), ("claims:global", 30)):
            if self.limiter.hit(bucket, limit, 3600) is not None:
                return self._outcome(
                    anchor, ClaimGenerationReceipt(ClaimGenerationStatus.RATE_LIMITED)
                )
        draft = await propose_claims(
            gateway or self.gateway,
            profile,
            self.cipher.decrypt(profile.api_key_encrypted),
            version,
        )
        status = ClaimGenerationStatus(draft.status)
        origin = None
        if draft.input_sha256 is not None and status is not ClaimGenerationStatus.UNAVAILABLE:
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
        revisions: tuple[ClaimRevision, ...] = ()
        if status is ClaimGenerationStatus.COMPLETED and origin is not None:
            try:
                revisions = build_proposal_batch(
                    version, draft.proposals, origin, actor_id, self.clock.now()
                )
            except ValueError:
                status, origin = ClaimGenerationStatus.INVALID, None
        # Provider-returned provenance is untrusted too; an invalid identifier must
        # produce a recorded failure rather than prevent the main report from saving.
        if origin is not None:
            try:
                origin.validate()
            except ValueError:
                status, origin, revisions = ClaimGenerationStatus.INVALID, None, ()
        receipt = ClaimGenerationReceipt(status, tuple(row.id for row in revisions), origin)
        receipt.validate()
        usage = (
            None
            if draft.status == "unsupported"
            else LlmUsage(
                at=self.clock.now(),
                profile_id=profile.id,
                user_id=actor_id,
                purpose="claim_proposals",
                ok=status in (ClaimGenerationStatus.COMPLETED, ClaimGenerationStatus.EMPTY),
                latency_ms=draft.latency_ms,
                prompt_tokens=draft.prompt_tokens,
                completion_tokens=draft.completion_tokens,
                error=None
                if status in (ClaimGenerationStatus.COMPLETED, ClaimGenerationStatus.EMPTY)
                else status.value,
            )
        )
        return self._outcome(anchor, receipt, revisions, usage)

    @staticmethod
    def _outcome(
        anchor: PendingAutomaticClaims,
        receipt: ClaimGenerationReceipt,
        revisions: tuple[ClaimRevision, ...] = (),
        usage: LlmUsage | None = None,
    ) -> PendingAutomaticClaims:
        return replace(anchor, receipt=receipt, revisions=revisions, usage=usage)
