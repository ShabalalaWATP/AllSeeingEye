"""One request-local answer with live access, bounded admission and usage accounting."""

import asyncio
import time
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from uuid import UUID

from ase.application.access import AccessPolicy
from ase.application.assistant.model import AssistantAnswerInvalid, answer_question
from ase.application.assistant.retrieval import AssistantRetrieval
from ase.application.assistant.usage import save_usage
from ase.application.model_routing import ModelRouting
from ase.application.ports import Clock, RateLimiter, UnitOfWork
from ase.application.ports.llm import (
    LlmGateway,
    LlmGatewayError,
    LlmTokenBudgetExhausted,
    SecretCipher,
)
from ase.application.ports.source_controls import SourceAdmission
from ase.domain.assistant import (
    AssistantAnswer,
    AssistantContext,
    AssistantModel,
    AssistantParagraph,
    AssistantQuestion,
)
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.llm import LlmProfile, LlmResult, LlmRole, LlmUsage
from ase.domain.users import User

SessionCheck = Callable[[], Awaitable[None]]
UsageRecorder = Callable[[LlmUsage], Awaitable[None]]
ANSWER_SECONDS = 120


class AssistantCapacity:
    """Fail fast rather than queue duplicate or unlimited model work."""

    def __init__(self, limit: int = 2) -> None:
        self.limit = limit
        self.active: set[UUID] = set()

    @contextmanager
    def reserve(self, actor_id: UUID) -> Iterator[None]:
        if actor_id in self.active or len(self.active) >= self.limit:
            raise RateLimited(5)
        self.active.add(actor_id)
        try:
            yield
        finally:
            self.active.discard(actor_id)


class MapAssistant:
    def __init__(
        self,
        access: AccessPolicy,
        routing: ModelRouting,
        retrieval: AssistantRetrieval,
        admission: SourceAdmission,
        gateway: LlmGateway,
        cipher: SecretCipher,
        clock: Clock,
        limiter: RateLimiter,
        uow: UnitOfWork,
        capacity: AssistantCapacity,
        record_usage: UsageRecorder,
    ) -> None:
        self.access, self.routing, self.retrieval = access, routing, retrieval
        self.admission, self.gateway, self.cipher = admission, gateway, cipher
        self.clock, self.limiter, self.uow = clock, limiter, uow
        self.capacity, self.record_usage = capacity, record_usage

    async def _authorise(
        self, actor: User, check_session: SessionCheck, *, final: bool = False
    ) -> None:
        try:
            access = await self.access.context(actor, for_update=final)
            access.require_create(None)
            await check_session()
        finally:
            # No identity-map snapshot or account lock crosses a provider request.
            await self.uow.rollback()

    async def _sources_enabled(self, context: AssistantContext) -> None:
        enabled = await self.admission.enabled_many(
            tuple(dict.fromkeys(source.source_id for source in context.sources))
        )
        if not all(enabled.get(source.source_id, False) for source in context.sources):
            raise InvalidRequest(
                "A source was disabled while answering. Ask again with current sources."
            )

    async def execute(
        self,
        actor: User,
        question: AssistantQuestion,
        *,
        check_session: SessionCheck,
    ) -> AssistantAnswer:
        retry = self.limiter.hit(f"map-assistant:{actor.id}", 6, 60)
        if retry is not None:
            raise RateLimited(retry)
        with self.capacity.reserve(actor.id):
            async with asyncio.timeout(ANSWER_SECONDS):
                await self._authorise(actor, check_session)
                context = replace(
                    await self.retrieval.collect(actor, question), as_of=self.clock.now()
                )
                if not context.sources:
                    async with self.admission.guard():
                        await self._authorise(actor, check_session, final=True)
                    return AssistantAnswer(
                        (
                            AssistantParagraph(
                                "gap",
                                context.clarification
                                or "No matching records were found in the bounded "
                                "retained map sample. This does not establish absence. "
                                "Name a source or place, select an item, or change the scope.",
                            ),
                        ),
                        context,
                        question,
                        self.clock.now(),
                    )
                try:
                    routing = await self.routing.snapshot(personal_owner_id=actor.id)
                    profile = routing.required(LlmRole.ASSESSMENT)
                finally:
                    await self.uow.rollback()
                return await self._answer(actor, question, context, profile, check_session)

    async def _answer(
        self,
        actor: User,
        question: AssistantQuestion,
        context: AssistantContext,
        profile: LlmProfile,
        check_session: SessionCheck,
    ) -> AssistantAnswer:
        result: LlmResult | None = None
        known: LlmTokenBudgetExhausted | AssistantAnswerInvalid | None = None
        started = time.perf_counter()
        sent = False
        error: str | None = None
        usage_saved = True
        try:
            async with self.admission.guard():
                await self._sources_enabled(context)
                await self._authorise(actor, check_session)
            sent = True
            paragraphs, result = await answer_question(
                self.gateway,
                self.cipher,
                profile,
                question,
                context,
            )
        except (AssistantAnswerInvalid, LlmTokenBudgetExhausted) as exc:
            known = exc
            error = (
                "invalid_answer"
                if isinstance(exc, AssistantAnswerInvalid)
                else "token_budget_exhausted"
            )
            raise InvalidRequest(str(exc)) from None
        except LlmGatewayError:
            error = "provider_failed"
            raise InvalidRequest(
                "The configured AI provider could not answer. No alternative model was used."
            ) from None
        except asyncio.CancelledError:
            error = "cancelled_or_timed_out"
            raise
        except BaseException:
            error = "answer_interrupted"
            raise
        finally:
            if sent:
                usage_saved = await save_usage(
                    self.record_usage,
                    LlmUsage(
                        at=self.clock.now(),
                        profile_id=profile.id,
                        user_id=actor.id,
                        purpose="map_assistant",
                        ok=error is None,
                        latency_ms=(time.perf_counter() - started) * 1000,
                        prompt_tokens=_tokens(
                            result.prompt_tokens
                            if result
                            else known.prompt_tokens
                            if known
                            else None
                        ),
                        completion_tokens=_tokens(
                            result.completion_tokens
                            if result
                            else known.completion_tokens
                            if known
                            else None
                        ),
                        error=error,
                    ),
                )
        if not usage_saved:
            context = replace(
                context,
                notes=(
                    *context.notes,
                    "Usage storage unconfirmed; the uncertain database write was not retried.",
                ),
            )
        # Accounting can await storage. Nothing protected is released until all
        # permissions have been rechecked after that final asynchronous side effect.
        async with self.admission.guard():
            await self._authorise(actor, check_session, final=True)
            await self._sources_enabled(context)
            await check_session()
            return AssistantAnswer(
                paragraphs,
                context,
                question,
                self.clock.now(),
                AssistantModel(
                    result.model,
                    profile.reasoning_effort.value if profile.reasoning_effort else None,
                ),
            )


def _tokens(value: int | None) -> int | None:
    return value if type(value) is int and 0 <= value <= 2**31 - 1 else None
