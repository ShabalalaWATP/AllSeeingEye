"""One request-local answer with live access, bounded admission and usage accounting."""

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import replace

from ase.application.access import AccessPolicy
from ase.application.assistant.continuation import AssistantCapacity
from ase.application.assistant.intent import interpret_question
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
    AssistantInterpretation,
    AssistantModel,
    AssistantParagraph,
    AssistantQuestion,
)
from ase.domain.errors import InvalidRequest, RateLimited
from ase.domain.events import Category
from ase.domain.llm import LlmProfile, LlmResult, LlmRole, LlmUsage
from ase.domain.users import User

SessionCheck = Callable[[], Awaitable[None]]
UsageRecorder = Callable[[LlmUsage], Awaitable[None]]
ANSWER_SECONDS = 120
FOLLOWUP_REFERENCE = re.compile(r"\b(those|these|them|earlier|previous|above)\b", re.I)


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
                if question.continuation_id:
                    previous = self.capacity.find(actor, question.continuation_id, self.clock.now())
                    if previous is None:
                        raise InvalidRequest(
                            "That Ask Eye conversation reference expired or is unavailable. "
                            "Start a new search."
                        )
                else:
                    previous = None
                if previous and FOLLOWUP_REFERENCE.search(question.question):
                    context = self._followup_context(previous, question)
                else:
                    context = await self.retrieval.collect(actor, question, as_of=self.clock.now())
                context = replace(context, as_of=self.clock.now())
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

    def _followup_context(
        self, previous: AssistantContext, question: AssistantQuestion
    ) -> AssistantContext:
        intent = interpret_question(question.question, now=self.clock.now())
        period = question.time_range or intent.time_range
        effective_categories = question.source_categories or (
            *(category.value for category in Category),
            "camera",
            "infrastructure",
            "doctrine",
        )
        interpretation = AssistantInterpretation(
            intent.topics,
            intent.countries,
            period.since if period else None,
            period.until if period else None,
            notes=("Reusing evidence from this user's earlier Ask Eye answer.",),
            source_categories=effective_categories,
        )
        if intent.clarification:
            return AssistantContext(
                (),
                0,
                0,
                False,
                ("No previous sources searched because the follow-up needs clarification.",),
                clarification=intent.clarification,
                interpretation=interpretation,
            )
        # Pronouns refer to the frozen evidence set. Analytical wording such as
        # "independently confirmed" is not a new entity that each title must contain.
        filter_intent = replace(
            intent,
            terms=tuple(term for term in intent.terms if term != "military"),
            anchors=(),
            residual=(),
        )
        rows = [
            source
            for source in previous.sources
            if _source_category(source) in effective_categories
            and filter_intent.accepts(_source_category(source), source)
            and (
                period is None
                or (
                    source.published_at is not None
                    and period.since <= source.published_at < period.until
                )
            )
            and (
                question.bbox is None
                or (source.point is not None and question.bbox.contains(source.point))
            )
            and (
                question.selected is None
                or (
                    source.kind == question.selected.kind
                    and source.record_id == question.selected.id
                )
            )
        ]
        return AssistantContext(
            tuple(replace(row, id=f"E{index + 1}") for index, row in enumerate(rows)),
            len(previous.sources),
            len({row.source_id for row in rows}),
            previous.capped,
            (
                *previous.notes,
                "Follow-up uses a frozen evidence packet; source status is rechecked.",
            ),
            matched_count=len(rows),
            interpretation=interpretation,
        )

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
            continuation_id = self.capacity.remember(actor, context, self.clock.now())
            return AssistantAnswer(
                paragraphs,
                context,
                question,
                self.clock.now(),
                AssistantModel(
                    result.model,
                    profile.reasoning_effort.value if profile.reasoning_effort else None,
                ),
                continuation_id,
            )


def _tokens(value: int | None) -> int | None:
    return value if type(value) is int and 0 <= value <= 2**31 - 1 else None


def _source_category(source: object) -> str:
    kind = getattr(source, "kind", "")
    if kind != "event":
        return str(kind)
    for detail in getattr(source, "details", ()):
        match = re.match(r"Category: ([a-z_]+);", detail)
        if match:
            return match.group(1)
    return "event"
