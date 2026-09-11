"""Prepare the private collection pool and its initial coverage receipt."""

from collections.abc import Callable
from dataclasses import replace

from ase.application.ports.feeds import EventStore
from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.ports.research import ResearchCollection
from ase.application.reports.fresh_web_research import FreshWebResearch
from ase.application.reports.plan_queries import prepare_model_plan
from ase.application.reports.production_types import Job, ProfileLookup, Totals
from ase.application.reports.progress import Progress, reached
from ase.application.reports.query_preparation import (
    prepare_query_languages,
    record_pass_provenance,
    record_query_translation,
    translation_languages,
)
from ase.application.reports.replan_queries import make_replanner
from ase.application.reports.research import collect_report_evidence
from ase.application.research.model_planning import record_planning
from ase.domain.direction import Direction
from ase.domain.research import ResearchQuery
from ase.domain.research_records import ResearchReceipt
from ase.domain.research_runs import ResearchStage
from ase.domain.validation import Finding, Severity
from ase.domain.web_research import WebResearchRecord


async def prepare_collection(
    job: Job,
    direction: Direction | None,
    totals: Totals,
    collection: ResearchCollection | None,
    store_factory: Callable[[], EventStore] | None,
    live_store: EventStore,
    progress: Progress | None,
    *,
    gateway: LlmGateway | None = None,
    cipher: SecretCipher | None = None,
    profile_for: ProfileLookup | None = None,
    web_research: FreshWebResearch | None = None,
) -> tuple[EventStore, ResearchReceipt | None, ResearchQuery | None]:
    store = live_store
    receipt: ResearchReceipt | None = None
    query: ResearchQuery | None = None
    if job.request.research_mode is not None:
        query = ResearchQuery(
            question=job.request.question or job.title,
            time_basis=job.request.effective_time_basis,
            since=job.period_from,
            until=job.period_to,
            languages=job.request.research_languages,
            source_ids=job.request.research_source_ids,
            query_variants=job.request.research_query_variants,
            candidate_hypotheses=job.request.research_candidate_hypotheses,
            planned_tasks=job.request.research_planned_tasks,
            terms=job.request.research_terms
            if job.request.research_terms is not None
            else tuple(direction.search_terms if direction else job.terms),
            mode=job.request.research_mode,
            focus=job.request.research_focus,
            country_iso=job.request.country_iso,
            country_isos=job.request.country_isos,
            research_web_search=job.request.research_web_search,
            subject=job.request.research_subject,
            area=job.request.effective_area,
        )
        if not query.terms:
            totals.findings.append(
                Finding(
                    "research_query_plan",
                    Severity.WARNING,
                    "research",
                    "No planned search terms are available. "
                    "Targeted query planning is missing; "
                    "collection receipts identify the sources actually attempted.",
                )
            )
        planning = None
        if gateway is not None and cipher is not None and profile_for is not None:
            query, planning = await prepare_model_plan(
                job,
                query,
                collection,
                totals,
                gateway,
                cipher,
                profile_for,
            )
        transformation = None
        if (
            collection is not None
            and gateway is not None
            and cipher is not None
            and profile_for
            and translation_languages(query)
        ):
            # Validate the actual inventory before spending translation tokens.
            preview = collection.plan(query)
            query, transformation = await prepare_query_languages(
                job,
                query,
                preview,
                totals,
                gateway,
                cipher,
                profile_for,
            )
        replan = None
        if (
            query.area is None
            and gateway is not None
            and cipher is not None
            and profile_for is not None
        ):
            replan = await make_replanner(job, totals, gateway, cipher, profile_for)
        await reached(progress, ResearchStage.COLLECTING)
        store, receipt = await collect_report_evidence(
            query,
            job.request,
            collection,
            store_factory,
            live_store,
            seed_events=job.seed_events,
            seed_attempts=job.seed_attempts,
            replan=replan,
        )
        if transformation is not None and receipt.plan is not None:
            receipt = replace(receipt, plan=record_query_translation(receipt.plan, transformation))
        receipt = record_pass_provenance(
            receipt,
            query,
            transformation,
            job.request.research_query_variants,
        )
        if planning is not None:
            receipt = replace(
                receipt,
                plan=record_planning(receipt.plan, planning) if receipt.plan else None,
                passes=tuple(
                    replace(row, plan=record_planning(row.plan, planning) if row.plan else None)
                    for row in receipt.passes
                ),
            )
        if query.research_web_search:
            web = (
                await web_research.collect(job, query, totals, cipher, profile_for)
                if web_research is not None and cipher is not None and profile_for is not None
                else WebResearchRecord(
                    "unavailable", "Fresh web search is not configured in this runtime.", job.now
                )
            )
            receipt = replace(receipt, web_research=web)
    return store, receipt, query
