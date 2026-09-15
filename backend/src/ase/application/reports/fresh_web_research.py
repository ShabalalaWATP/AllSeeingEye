"""Run explicit live search with the destination's immutable direction profile."""

import asyncio
import time
from dataclasses import replace

from ase.application.ai_usage import AiUsageAccounting
from ase.application.ai_usage_gateway import AllowanceWebSearchGateway
from ase.application.ports.llm import SecretCipher
from ase.application.ports.services import Clock, RateLimiter
from ase.application.ports.source_controls import SourceAdmission
from ase.application.ports.web_search import (
    DEFAULT_WEB_OUTPUT_TOKENS,
    MAX_WEB_OUTPUT_TOKENS,
    WebSearchError,
    WebSearchGateway,
    WebSearchRequest,
    WebSearchUsageSink,
)
from ase.application.report_jobs.budget import JobBudgetExhausted
from ase.application.report_jobs.fresh_web_allocation import validate_web_discovery_plan
from ase.application.reports.fresh_web_context import web_query_context
from ase.application.reports.production_types import Job, ProfileLookup, Totals
from ase.domain.errors import EncryptionUnavailable
from ase.domain.llm import LlmProfile, LlmProvider, LlmRole, LlmUsage
from ase.domain.research import ResearchFocus, ResearchQuery
from ase.domain.validation import Finding, Severity
from ase.domain.web_research import (
    WEB_ALLOCATED_OUTPUT_TOKENS,
    WEB_ALLOCATED_REQUESTS,
    WEB_ALLOCATED_SECONDS,
    WEB_ALLOCATED_TOOL_CALLS,
    WEB_ALLOCATION_POLICY,
    WEB_SOURCE_ID,
    WebResearchRecord,
)


class FreshWebResearch:
    def __init__(
        self,
        gateway: WebSearchGateway,
        admission: SourceAdmission,
        clock: Clock,
        limiter: RateLimiter,
        usage_sink: WebSearchUsageSink | None = None,
        ai_usage: AiUsageAccounting | None = None,
        *,
        allocation_plan: object | None = None,
    ) -> None:
        self._gateway, self._admission = gateway, admission
        self._clock, self._limiter = clock, limiter
        self._usage_sink = usage_sink
        self._ai_usage = ai_usage
        self._allocated = (
            validate_web_discovery_plan(allocation_plan) if allocation_plan is not None else None
        )

    async def collect(
        self,
        job: Job,
        query: ResearchQuery,
        totals: Totals,
        cipher: SecretCipher,
        profile_for: ProfileLookup,
    ) -> WebResearchRecord:
        record = WebResearchRecord(
            "not_collected",
            "Fresh web search was not selected.",
            self._clock.now(),
            allocation_version=WEB_ALLOCATION_POLICY if self._allocated is not None else None,
            allocated_requests=WEB_ALLOCATED_REQUESTS if self._allocated is not None else 0,
            allocated_tool_calls=WEB_ALLOCATED_TOOL_CALLS if self._allocated is not None else 0,
            allocated_seconds=WEB_ALLOCATED_SECONDS if self._allocated is not None else 0,
            allocated_output_tokens=(
                WEB_ALLOCATED_OUTPUT_TOKENS if self._allocated is not None else 0
            ),
        )
        prepared = await self._profile(query, profile_for, record)
        if isinstance(prepared, WebResearchRecord):
            return prepared
        profile = prepared
        record = replace(
            record,
            requested_model=profile.model,
            profile_id=profile.id,
            profile_revision=profile.revision,
        )
        inputs = await self._inputs(job, query, profile, cipher, record)
        if isinstance(inputs, WebResearchRecord):
            return inputs
        context, key = inputs
        output_budget = min(profile.token_budget(DEFAULT_WEB_OUTPUT_TOKENS), MAX_WEB_OUTPUT_TOKENS)
        started = time.perf_counter()
        try:
            gateway: WebSearchGateway = self._gateway
            if self._ai_usage is not None:
                gateway = AllowanceWebSearchGateway(
                    gateway,
                    self._ai_usage,
                    owner_id=job.actor.id,
                    team_id=job.request.team_id,
                    profile_id=profile.id,
                )
            async with asyncio.timeout(WEB_ALLOCATED_SECONDS):
                result = await gateway.search(
                    key,
                    profile.model,
                    WebSearchRequest(context, output_budget, profile.reasoning_effort),
                )
            record = replace(
                record,
                status="failed" if result.failure else "completed",
                explanation=result.failure
                or (
                    "A live web search completed. Generated context and cited links are "
                    "saved separately from dated, graded evidence. Up to three tool calls "
                    "share a separate 90-second deadline and a ceiling of "
                    f"{output_budget:,} output tokens, including reasoning."
                ),
                retrieved_at=self._clock.now(),
                returned_model=result.model,
                synthesis=result.synthesis,
                citations=result.citations,
                consulted_urls=result.consulted_urls,
                tool_calls=result.tool_calls,
                request_count=1,
                latency_ms=result.latency_ms,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
            )
            async with self._admission.guard():
                if not await self._admission.enabled(WEB_SOURCE_ID):
                    record = self._disabled(record)
        except JobBudgetExhausted:
            return replace(
                record,
                status="not_collected",
                explanation=(
                    "The frozen fresh-web discovery allowance was exhausted before dispatch."
                    if self._allocated is not None
                    else "The report's model-call allowance was exhausted before web dispatch."
                ),
                retrieved_at=self._clock.now(),
            )
        except (WebSearchError, TimeoutError) as exc:
            timeout = isinstance(exc, TimeoutError) or "deadline" in str(exc)
            record = replace(
                record,
                status="timed_out" if timeout else "failed",
                request_count=1,
                synthesis="",
                citations=(),
                consulted_urls=(),
                explanation="The web search exceeded its deadline." if timeout else str(exc),
                latency_ms=(time.perf_counter() - started) * 1000,
            )
        except asyncio.CancelledError:
            await self._account(
                job,
                profile,
                totals,
                replace(
                    record,
                    status="failed",
                    request_count=1,
                    synthesis="",
                    citations=(),
                    consulted_urls=(),
                    explanation=(
                        "Web research was cancelled before result release."
                        if record.request_count
                        else "The web search was cancelled; final provider usage is unknown."
                    ),
                    latency_ms=(time.perf_counter() - started) * 1000,
                ),
            )
            raise
        await self._account(job, profile, totals, record)
        return record

    async def _profile(
        self,
        query: ResearchQuery,
        profile_for: ProfileLookup,
        record: WebResearchRecord,
    ) -> LlmProfile | WebResearchRecord:
        if not query.research_web_search:
            return record
        if query.focus in {ResearchFocus.DOCUMENT, ResearchFocus.MEDIA}:
            return replace(
                record,
                status="unsupported",
                explanation=(
                    "Private media and document contents are not sent to public web search. "
                    "Start a separate public research question to search for public context."
                ),
            )
        if not await self._admission.enabled(WEB_SOURCE_ID):
            return self._disabled(record)
        profile = await profile_for(LlmRole.DIRECTION)
        if profile is None:
            return replace(
                record,
                status="unavailable",
                explanation=(
                    "No enabled direction model is assigned to this research destination."
                ),
            )
        record = replace(
            record,
            requested_model=profile.model,
            profile_id=profile.id,
            profile_revision=profile.revision,
        )
        if (
            not profile.allows(LlmRole.DIRECTION)
            or profile.provider is not LlmProvider.OPENAI_COMPATIBLE
            or profile.base_url.rstrip("/").lower() != "https://api.openai.com/v1"
        ):
            return replace(
                record,
                status="unsupported",
                explanation=(
                    "Fresh web search currently requires an OpenAI direction profile using "
                    "https://api.openai.com/v1 and a model with web-search support. "
                    "The selected provider was preserved; app sources can still be researched."
                ),
            )
        return profile

    async def _inputs(
        self,
        job: Job,
        query: ResearchQuery,
        profile: LlmProfile,
        cipher: SecretCipher,
        record: WebResearchRecord,
    ) -> tuple[str, str] | WebResearchRecord:
        context = web_query_context(query)
        if context is None:
            return replace(
                record,
                status="unsupported",
                explanation=(
                    "This area's geometry exceeds the bounded web-search context limit. "
                    "App source collection is unaffected."
                ),
            )
        try:
            key = cipher.decrypt(profile.api_key_encrypted)
        except EncryptionUnavailable:
            return replace(
                record,
                status="unavailable",
                explanation=("The selected direction profile's credential could not be decrypted."),
            )
        if not key:
            return replace(
                record,
                status="unavailable",
                explanation=("The selected direction profile needs an OpenAI API key."),
            )
        for name, limit in ((f"web-search:user:{job.actor.id}", 6), ("web-search:global", 24)):
            if self._limiter.hit(name, limit, 3600) is not None:
                return replace(
                    record,
                    status="unavailable",
                    explanation=(
                        "The fresh-web search rate limit has been reached. Try again later."
                    ),
                )
        # A source can be disabled during profile resolution. Check again before dispatch.
        if not await self._admission.enabled(WEB_SOURCE_ID):
            return self._disabled(record)
        return context, key

    @staticmethod
    def _disabled(record: WebResearchRecord) -> WebResearchRecord:
        return replace(
            record,
            status="unavailable",
            synthesis="",
            citations=(),
            consulted_urls=(),
            explanation=(
                "The administrator disabled fresh web search. No web context was admitted."
            ),
        )

    async def _account(
        self, job: Job, profile: LlmProfile, totals: Totals, record: WebResearchRecord
    ) -> None:
        ok = record.status == "completed"
        call = LlmUsage(
            at=record.retrieved_at,
            profile_id=profile.id,
            user_id=job.actor.id,
            purpose=f"report:{job.template.id}:fresh_web_search",
            ok=ok,
            latency_ms=record.latency_ms,
            prompt_tokens=record.prompt_tokens,
            completion_tokens=record.completion_tokens,
            error=None if ok else record.explanation[:500],
        )
        totals.add(record.prompt_tokens, record.completion_tokens, record.latency_ms, ())
        if self._usage_sink is None:
            totals.usage.append(call)
        elif not await self._save_usage(call):
            # A commit may have succeeded before a close/timeout error. Retrying via
            # final report persistence could insert this attempt twice.
            totals.findings.append(
                Finding(
                    "fresh_web_usage",
                    Severity.WARNING,
                    "research.web_research",
                    "Fresh web usage storage could not be confirmed. Check provider usage; "
                    "the app did not retry an uncertain database write.",
                )
            )
        if not ok:
            totals.findings.append(
                Finding(
                    "fresh_web_search",
                    Severity.WARNING,
                    "research.web_research",
                    record.explanation,
                )
            )

    async def _save_usage(self, call: LlmUsage) -> bool:
        if self._usage_sink is None:
            return False
        pending = asyncio.ensure_future(self._usage_sink(call))
        deadline = time.perf_counter() + 3
        try:
            async with asyncio.timeout(3):
                await asyncio.shield(pending)
        except asyncio.CancelledError:
            # Cancellation of report work does not cancel a short bookkeeping commit.
            try:
                async with asyncio.timeout(max(0, deadline - time.perf_counter())):
                    await asyncio.shield(pending)
            except (Exception, asyncio.CancelledError):
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
            raise
        except Exception:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
            return False
        return True
