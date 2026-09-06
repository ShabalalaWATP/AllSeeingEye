"""Production collection freezes transformations without changing scope or operator input."""

import json
from dataclasses import replace

import pytest

from ase.api.schemas_research_plan import ResearchPlanOut
from ase.application.reports.production_collection import prepare_collection
from ase.application.reports.production_types import Totals
from ase.application.reports.query_preparation import record_pass_provenance
from ase.application.research.service import ResearchCollectionService
from ase.container.research import private_research_store
from ase.domain.llm import LlmRole
from ase.domain.research import CollectionPass, ResearchFocus, ResearchMode
from ase.domain.research_plan import QueryTransformation, QueryVariant
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from production_integration_helpers import production_job
from test_query_translation import Gateway
from test_research_plan import QUERY, Provider


@pytest.mark.parametrize("outcome", ["completed", "failed", "unavailable"])
async def test_production_routes_and_freezes_translation(container, user, outcome):

    provider = Provider("persian", "fa")
    collection = ResearchCollectionService(lambda query: [provider])
    job = production_job(user, container.cipher)
    job = replace(
        job,
        request=replace(
            job.request,
            research_mode=ResearchMode.QUICK,
            research_languages=("fa",),
            research_terms=("oil",),
        ),
    )
    gateway = Gateway(
        json.dumps({"variants": [{"language": "fa", "terms": ["نفت"]}]})
        if outcome == "completed"
        else "invalid"
    )
    roles = []

    async def lookup(role):
        roles.append(role)
        return None if outcome == "unavailable" or role is LlmRole.DIRECTION else job.profile

    totals = Totals()
    _, receipt, query = await prepare_collection(
        job,
        None,
        totals,
        collection,
        private_research_store,
        container.store,
        None,
        gateway=gateway,
        cipher=container.cipher,
        profile_for=lookup,
    )
    assert query is not None and receipt is not None and receipt.plan is not None
    assert roles == [LlmRole.TRANSLATION, LlmRole.DIRECTION]
    assert receipt.plan.translation.status == outcome
    assert receipt.plan.translation.original_terms == ("oil",)
    assert receipt.plan.translation_calls == int(outcome != "unavailable")
    assert len(totals.usage) == gateway.calls == int(outcome != "unavailable")
    assert provider.queries[0].terms == (("نفت",) if outcome == "completed" else ("oil",))
    assert receipt.plan.tasks[0].provenance == (
        "machine_translated_variant" if outcome == "completed" else "original_terms"
    )
    assert research_from_dict(research_to_dict(receipt)) == receipt
    assert ResearchPlanOut.model_validate(receipt.plan).translation.status == outcome


@pytest.mark.parametrize("skip", ["document", "media", "empty", "operator", "english", "long"])
async def test_no_unsolicited_translation(container, user, skip):
    provider = Provider("persian", "fa")
    collection = ResearchCollectionService(lambda query: [provider])
    job = production_job(user, container.cipher)
    request = replace(
        job.request,
        research_mode=ResearchMode.QUICK,
        research_languages=("fa",),
        research_terms=("private terms",),
    )
    if skip in {"document", "media"}:
        request = replace(request, research_focus=ResearchFocus(skip))
    elif skip == "empty":
        request = replace(request, research_source_ids=())
    elif skip == "operator":
        request = replace(request, research_query_variants=(QueryVariant("fa", ("provided",)),))
    elif skip == "long":
        request = replace(request, research_terms=("x" * 300,) * 4)
    else:
        request = replace(request, research_languages=("en",))
    job = replace(job, request=request)

    async def lookup(role):
        assert role is LlmRole.DIRECTION

    gateway = Gateway()
    await prepare_collection(
        job,
        None,
        Totals(),
        collection,
        private_research_store,
        container.store,
        None,
        gateway=gateway,
        cipher=container.cipher,
        profile_for=lookup,
    )
    assert gateway.calls == 0
    if skip == "operator":
        assert provider.queries[0].terms == ("provided",)


def test_replan_of_only_translated_terms_is_not_labelled_as_initial_translation():

    original = replace(
        QUERY, languages=("fa",), query_variants=(QueryVariant("fa", ("initial translation",)),)
    )
    revised = replace(original, query_variants=(QueryVariant("fa", ("revised translation",)),))
    collection = ResearchCollectionService(lambda query: [Provider("persian", "fa")])
    revised_plan = replace(collection.plan(revised), replans=1)
    receipt = ResearchReceipt.build(
        original,
        (),
        0,
        collection.plan(original),
        (CollectionPass(original.terms, (), revised_plan),),
    )
    transformation = QueryTransformation(
        original.terms, ("fa",), "first-model", "completed", original.query_variants
    )
    result = record_pass_provenance(receipt, original, transformation, ())
    assert result.passes[0].plan.tasks[0].provenance == "model_replanned_variant"
    assert result.passes[0].plan.translation is None
