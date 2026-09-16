"""One model call, checked mechanically, retried once with the errors, then given up on."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from pydantic import ValidationError

from ase.application.ports import Clock
from ase.application.ports.llm import LlmGateway, LlmGatewayError, SecretCipher
from ase.application.ukraine_digest_evidence import EvidencePack
from ase.application.ukraine_digest_model import CALL_SECONDS, MAX_OUTPUT_BYTES, digest_request
from ase.application.ukraine_digest_validation import validate_digest
from ase.domain.ai_usage import AiAllowanceExceeded
from ase.domain.llm import LlmProfile, LlmResult, LlmUsage
from ase.domain.ukraine.digest import DigestCitation, UkraineDigest

PURPOSE = "ukraine_digest"
ATTEMPTS = 2
UsageRecorder = Callable[[LlmUsage], Awaitable[None]]


class DigestRejected(Exception):
    """The answer failed the mechanical checks on every attempt; nothing is stored."""

    def __init__(self, errors: tuple[str, ...]) -> None:
        super().__init__("The digest failed its mechanical checks.")
        self.errors = errors


@dataclass(frozen=True, slots=True)
class WrittenDigest:
    """A validated digest with the counts and frozen citations that go into storage."""

    digest: UkraineDigest
    model: str
    citations: tuple[DigestCitation, ...]
    prompt_tokens: int | None
    completion_tokens: int | None


def cited(digest: UkraineDigest, pack: EvidencePack) -> tuple[DigestCitation, ...]:
    """Freeze only the evidence the digest actually names, in pack order."""
    named = {key for change in digest.changes() for key in change.source_ids}
    return tuple(
        DigestCitation(
            id=item.id,
            kind=item.kind,
            source_id=item.source_id,
            label=item.label,
            dated_on=item.dated_on,
            url=item.url,
        )
        for item in pack.items
        if item.id in named
    )


class DigestWriter:
    def __init__(
        self,
        gateway: LlmGateway,
        cipher: SecretCipher,
        clock: Clock,
        record_usage: UsageRecorder,
    ) -> None:
        self._gateway, self._cipher = gateway, cipher
        self._clock, self._record_usage = clock, record_usage

    async def write(self, profile: LlmProfile, pack: EvidencePack) -> WrittenDigest:
        """Call once, check, and on failure call once more with the errors. Then stop."""
        errors: tuple[str, ...] = ()
        for _ in range(ATTEMPTS):
            digest, result = await self._attempt(profile, pack, errors)
            errors = validate_digest(digest, pack)
            if not errors:
                return WrittenDigest(
                    digest,
                    result.model,
                    cited(digest, pack),
                    result.prompt_tokens,
                    result.completion_tokens,
                )
        raise DigestRejected(errors)

    async def _attempt(
        self, profile: LlmProfile, pack: EvidencePack, corrections: tuple[str, ...]
    ) -> tuple[UkraineDigest, LlmResult]:
        key = self._decrypt(profile)
        request = digest_request(profile, pack, corrections)
        usage = LlmUsage(
            at=self._clock.now(),
            profile_id=profile.id,
            user_id=None,
            purpose=PURPOSE,
            ok=False,
            latency_ms=0.0,
        )
        started = time.perf_counter()
        digest: UkraineDigest | None = None
        result: LlmResult | None = None
        try:
            async with asyncio.timeout(CALL_SECONDS):
                result = await self._gateway.complete(profile.base_url, key, profile.model, request)
            usage.latency_ms = result.latency_ms
            usage.prompt_tokens = result.prompt_tokens
            usage.completion_tokens = result.completion_tokens
            if len(result.content.encode()) > MAX_OUTPUT_BYTES:
                raise ValueError("Oversized digest output")
            digest = UkraineDigest.model_validate_json(result.content)
            usage.ok = True
        except AiAllowanceExceeded:
            # Refused before dispatch: no provider usage exists to record.
            raise LlmGatewayError("The system AI allowance is exhausted.") from None
        except TimeoutError:
            usage.error = "The digest model timed out."
        except (ValidationError, ValueError, RecursionError):
            usage.error = "The digest model returned an invalid response."
        except Exception:
            usage.error = "The digest model call failed."
        # Cancellation intentionally propagates without recording an outcome.
        if not usage.ok:
            usage.latency_ms = (time.perf_counter() - started) * 1_000
        await self._save(usage)
        if usage.error is not None or digest is None or result is None:
            raise LlmGatewayError(usage.error or "The digest model call failed.")
        return digest, result

    def _decrypt(self, profile: LlmProfile) -> str:
        try:
            if not self._cipher.available:
                raise ValueError("Encryption is unavailable.")
            return self._cipher.decrypt(profile.api_key_encrypted)
        except Exception:
            # Cipher implementations have provider-specific failures; none may expose secrets.
            raise LlmGatewayError("The digest model configuration is unavailable.") from None

    async def _save(self, usage: LlmUsage) -> None:
        try:
            await self._record_usage(usage)
        except Exception:
            raise LlmGatewayError("Digest usage could not be recorded.") from None
