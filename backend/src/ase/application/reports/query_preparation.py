"""Use frozen report routing for optional query translation before public collection."""

from dataclasses import replace

from ase.application.ports.llm import LlmGateway, SecretCipher
from ase.application.reports.production_types import Job, ProfileLookup, Totals, usage_entry
from ase.application.research.query_translation import translate_queries
from ase.domain.languages import language_capability
from ase.domain.llm import LlmRole
from ase.domain.research import ResearchFocus, ResearchQuery
from ase.domain.research_plan import QueryTransformation, ResearchPlan
from ase.domain.validation import Finding, Severity


def translation_languages(query: ResearchQuery) -> tuple[str, ...]:
    if (
        not query.terms
        or query.source_ids == ()
        or query.focus in {ResearchFocus.DOCUMENT, ResearchFocus.MEDIA}
    ):
        return ()
    supplied = {variant.language.lower() for variant in query.query_variants}
    return tuple(
        language
        for language in query.languages
        if language.lower() not in supplied
        and language.lower() != "en"
        and language_capability(language) is not None
    )


async def prepare_query_languages(
    job: Job,
    query: ResearchQuery,
    plan: ResearchPlan,
    totals: Totals,
    gateway: LlmGateway,
    cipher: SecretCipher,
    profile_for: ProfileLookup,
) -> tuple[ResearchQuery, QueryTransformation | None]:
    """Explicit operator variants win. Private input and empty selection make no call."""
    languages = translation_languages(query)
    if not languages or not any(task.selected and task.supported for task in plan.tasks):
        return query, None
    if sum(map(len, query.terms)) > 1000:
        totals.findings.append(
            Finding(
                "query_translation",
                Severity.WARNING,
                "research",
                "Original terms exceed the translation input budget; no translation call was made.",
            )
        )
        return query, None
    profile = await profile_for(LlmRole.TRANSLATION)
    if profile is None:
        return query, QueryTransformation(query.terms, languages, "", "unavailable")
    call = await translate_queries(
        gateway, profile, cipher.decrypt(profile.api_key_encrypted), query.terms, languages
    )
    totals.usage.append(
        usage_entry(job, profile, "research:query_translation", bool(call.variants), call)
    )
    totals.add(call.prompt_tokens, call.completion_tokens, call.latency_ms, call.findings)
    transformation = QueryTransformation(
        query.terms,
        languages,
        call.model,
        "completed" if call.variants else "failed",
        call.variants,
    )
    return replace(query, query_variants=(*query.query_variants, *call.variants)), transformation


def record_query_translation(
    plan: ResearchPlan,
    transformation: QueryTransformation,
) -> ResearchPlan:
    generated = {variant.language.lower() for variant in transformation.variants}
    calls = int(transformation.status != "unavailable")
    return replace(
        plan,
        translation=transformation,
        translation_calls=calls,
        model_calls=plan.model_calls + calls,
        tasks=tuple(
            replace(task, provenance="machine_translated_variant")
            if task.query_language and task.query_language.lower() in generated
            else task
            for task in plan.tasks
        ),
    )
