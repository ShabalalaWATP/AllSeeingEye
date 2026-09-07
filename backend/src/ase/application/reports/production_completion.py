"""Finish optional model stages before acquiring report persistence guards."""

from collections.abc import Awaitable, Callable

from ase.application.ports.llm import LlmUsageRepository
from ase.application.reports.automatic_claims import AutomaticClaims
from ase.application.reports.production_result import ProductionResult
from ase.application.reports.production_types import Job, ProfileLookup, Totals
from ase.application.reports.progress import Progress, reached
from ase.domain.report_records import ReportVersion
from ase.domain.research_runs import ResearchStage


async def complete_production(
    version: ReportVersion,
    job: Job,
    totals: Totals,
    automatic_claims: AutomaticClaims | None,
    profile_for: ProfileLookup,
    before_persist: Callable[[], Awaitable[None]] | None,
    progress: Progress | None,
    usage: LlmUsageRepository,
) -> ProductionResult:
    pending = None
    if automatic_claims is not None:
        pending = await automatic_claims.prepare(version, job.actor.id, profile_for)
        if pending.usage is not None:
            call = pending.usage
            totals.usage.append(call)
            totals.add(call.prompt_tokens, call.completion_tokens, call.latency_ms, ())
            version.prompt_tokens = totals.prompt_tokens
            version.completion_tokens = totals.completion_tokens
            version.latency_ms = totals.latency_ms
    if before_persist is not None:
        await before_persist()
    await reached(progress, ResearchStage.SAVING)
    for item in totals.usage:
        await usage.add(item)
    return ProductionResult(version, pending)
