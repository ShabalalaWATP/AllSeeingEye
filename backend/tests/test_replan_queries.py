"""Model revisions cannot alter identifiers, operators' variants or research scope."""

import asyncio
import json
from dataclasses import replace

import pytest

from ase.application.reports.production_types import Totals
from ase.application.reports.replan_queries import make_replanner, revised_query
from ase.application.reports.research_export import research_sections
from ase.application.research.service import ResearchCollectionService
from ase.domain.research import ResearchBatch, ResearchMode
from ase.domain.research_plan import QueryVariant
from ase.domain.research_records import ResearchReceipt, research_from_dict, research_to_dict
from production_integration_helpers import production_job
from test_query_translation import Gateway
from test_research_plan import QUERY, Provider


def proposal(terms=("revised",)):
    return json.dumps({"terms": terms, "variants": [{"language": "en", "terms": terms}]})


def test_revised_query_only_changes_terms_and_generated_variants():
    revised = revised_query(proposal(), QUERY, ())
    assert replace(revised, terms=QUERY.terms, query_variants=QUERY.query_variants) == QUERY
    assert revised.terms == ("revised",)


@pytest.mark.parametrize(
    "payload",
    [
        "invalid",
        "{}",
        "[]",
        '{"terms":[],"variants":[]}',
        '{"terms":[42],"variants":[]}',
        '{"terms":["new"],"variants":[],"source_ids":["other"]}',
    ],
)
def test_malformed_or_scope_proposals_are_rejected(payload):
    with pytest.raises(ValueError):
        revised_query(payload, QUERY, ())


def test_identifiers_and_fixed_variants_survive():
    original = replace(QUERY, terms=('"Acme" 123',), languages=("en", "fa"))
    fixed = (QueryVariant("fa", ("operator phrase",)),)
    result = revised_query(proposal(('"Acme" 123 revised',)), original, fixed)
    assert result.query_variants[0] == fixed[0]
    with pytest.raises(ValueError):
        revised_query(proposal(('"Acme" 1234 revised',)), original, fixed)


async def test_model_callback_collects_twice_and_freezes_both_passes(container, user):
    job = production_job(user, container.cipher)
    job = replace(job, request=replace(job.request, research_mode=ResearchMode.QUICK))
    totals = Totals()
    gateway = Gateway(proposal())

    async def lookup(role):
        return job.profile

    callback = await make_replanner(job, totals, gateway, container.cipher, lookup)
    provider = Provider("fixture")
    service = ResearchCollectionService(lambda query: [provider])
    batch = await service.collect(QUERY, replan=callback)
    assert gateway.calls == 1 and len(provider.queries) == 2
    assert provider.queries[1].terms == ("revised",)
    assert batch.plan.replans == batch.plan.model_calls == 1
    assert [item.terms for item in batch.passes] == [QUERY.terms, ("revised",)]
    assert totals.usage[0].purpose == "research:replan" and totals.usage[0].ok
    receipt = ResearchReceipt.build(
        QUERY, batch.attempts, len(batch.items), batch.plan, batch.passes
    )
    encoded = json.loads(json.dumps(research_to_dict(receipt)))
    assert research_from_dict(encoded) == receipt
    exported = str(research_sections(receipt))
    assert "Collection pass 2" in exported and "revised" in exported


async def test_callback_cancellation_keeps_attempt_accounting(container, user):
    job = production_job(user, container.cipher)
    totals = Totals()

    class CancelledGateway:
        async def complete(self, *args):
            raise asyncio.CancelledError

    async def lookup(role):
        return job.profile

    callback = await make_replanner(job, totals, CancelledGateway(), container.cipher, lookup)
    with pytest.raises(asyncio.CancelledError):
        await callback(QUERY, ResearchBatch(), 10)
    assert len(totals.usage) == 1 and not totals.usage[0].ok


async def test_invalid_model_revision_retains_original_query(container, user):
    job = production_job(user, container.cipher)
    totals = Totals()

    async def lookup(role):
        return job.profile

    callback = await make_replanner(job, totals, Gateway("bad"), container.cipher, lookup)
    assert await callback(QUERY, ResearchBatch(), 10) is None
    assert len(totals.usage) == 1 and not totals.usage[0].ok
    assert totals.findings[0].rule == "research_replan"
