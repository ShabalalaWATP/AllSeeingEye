"""One structured model call, parsed and mechanically checked, with a single retry."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from ase.application.economy_explainer_facts import FactPack
from ase.application.economy_explainer_prompt import SCHEMA_NAME, explainer_request
from ase.application.economy_explainer_validation import validate_explainer
from ase.application.ports import Clock
from ase.application.ports.llm import LlmGateway, LlmGatewayError, SecretCipher
from ase.domain.ai_usage import AiAllowanceExceeded
from ase.domain.economy_explainer import ExplainerText, from_payload
from ase.domain.llm import LlmProfile, LlmUsage

CALL_SECONDS = 90
MAX_ATTEMPTS = 2
MAX_OUTPUT_BYTES = 96 * 1024
UsageRecorder = Callable[[LlmUsage], Awaitable[None]]
REASONS = {
    "allowance_exhausted": (
        "The AI usage allowance is spent, so no written summary was produced. "
        "The figures on this page are unaffected."
    ),
    "model_unavailable": (
        "No model is available for written summaries at the moment. "
        "The figures on this page are unaffected."
    ),
    "model_failed": (
        "The model could not be reached or returned an answer that could not be read. "
        "The figures on this page are unaffected."
    ),
    "validation_failed": (
        "A written summary was produced but it failed the automatic checks against the "
        "figures, so it was discarded. The figures on this page are the source of truth."
    ),
}


@dataclass(slots=True)
class GenerationOutcome:
    text: ExplainerText | None = None
    model: str = ""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    problems: tuple[str, ...] = ()
    failure: str | None = None
    attempts: int = 0
    usage: list[LlmUsage] = field(default_factory=list)

    @property
    def reason(self) -> str | None:
        return REASONS.get(self.failure or "")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate explainer JSON key.")
        value[key] = item
    return value


def _invalid_constant(_value: str) -> None:
    raise ValueError("Invalid explainer JSON number.")


def parse_explainer(content: str) -> ExplainerText:
    if len(content.encode("utf-8")) > MAX_OUTPUT_BYTES:
        raise ValueError("The explainer response exceeds its byte budget.")
    data = json.loads(content, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    if not isinstance(data, dict):
        raise ValueError("The explainer response is not an object.")
    return from_payload(data)


class ExplainerGenerator:
    """Owns the provider call only. Routing, admission and storage stay with the caller."""

    def __init__(
        self,
        gateway: LlmGateway,
        cipher: SecretCipher,
        clock: Clock,
        record_usage: UsageRecorder | None = None,
    ) -> None:
        self._gateway, self._cipher, self._clock = gateway, cipher, clock
        self._record_usage = record_usage

    async def generate(self, profile: LlmProfile, pack: FactPack) -> GenerationOutcome:
        outcome = GenerationOutcome()
        try:
            if not self._cipher.available:
                raise ValueError("Encryption is unavailable.")
            key = self._cipher.decrypt(profile.api_key_encrypted)
        except Exception:
            # Cipher failures are provider specific; none of them may expose a secret.
            outcome.failure = "model_unavailable"
            return outcome
        for attempt in range(1, MAX_ATTEMPTS + 1):
            outcome.attempts = attempt
            content = await self._call(profile, key, pack, outcome)
            if content is None:
                return outcome
            try:
                text = parse_explainer(content)
            except (ValueError, RecursionError) as exc:
                outcome.problems = (f"the answer could not be read: {exc}",)
                outcome.failure = "validation_failed"
                continue
            problems = validate_explainer(text, pack)
            if not problems:
                outcome.text, outcome.failure, outcome.problems = text, None, ()
                return outcome
            outcome.problems = tuple(problems)
            outcome.failure = "validation_failed"
        return outcome

    async def _call(
        self, profile: LlmProfile, key: str, pack: FactPack, outcome: GenerationOutcome
    ) -> str | None:
        """Return the raw answer, or None when the failure must stop the whole attempt."""
        usage = LlmUsage(
            at=self._clock.now(),
            profile_id=profile.id,
            user_id=None,
            purpose=SCHEMA_NAME,
            ok=False,
            latency_ms=0.0,
        )
        started = time.perf_counter()
        try:
            request = explainer_request(profile, pack, outcome.problems)
            async with asyncio.timeout(CALL_SECONDS):
                result = await self._gateway.complete(profile.base_url, key, profile.model, request)
        except AiAllowanceExceeded:
            outcome.failure = "allowance_exhausted"
            return None
        except (LlmGatewayError, TimeoutError, ValueError):
            usage.error = "The economy explainer model call failed."
            usage.latency_ms = (time.perf_counter() - started) * 1_000
            await self._record(usage)
            outcome.failure = "model_failed"
            return None
        usage.ok = True
        usage.latency_ms = result.latency_ms
        usage.prompt_tokens, usage.completion_tokens = (
            result.prompt_tokens,
            result.completion_tokens,
        )
        await self._record(usage)
        outcome.model = result.model or profile.model
        outcome.prompt_tokens = (outcome.prompt_tokens or 0) + (result.prompt_tokens or 0)
        outcome.completion_tokens = (outcome.completion_tokens or 0) + (
            result.completion_tokens or 0
        )
        return result.content

    async def _record(self, usage: LlmUsage) -> None:
        if self._record_usage is None:
            return
        try:
            await self._record_usage(usage)
        except Exception:
            # Usage recording must never turn a completed call into an unhandled failure.
            return
