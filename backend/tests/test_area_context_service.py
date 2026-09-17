"""The service that decides whether a report sees the map at all, and what it then sees.

The restraint cases come first: an ordinary question must leave the receipt untouched
and must not read a single live record, however much the map happens to hold.
"""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from ase.adapters.geo.area_geography import PackagedAreaGeography
from ase.application.reports.area_context import AreaContextService, attach_area_context
from ase.application.reports.selection import Selection
from ase.domain.events import Category
from ase.domain.research import ResearchMode
from ase.domain.research_records import ResearchReceipt
from production_integration_helpers import production_job
from test_area_instrument_sweep import KYIV_REGION, NOW, Cells, Store, event
from test_asset_register_research import box  # noqa: F401 - re-exported area builder

CAPTURED = datetime(2026, 9, 15, tzinfo=UTC)
RECEIPT = ResearchReceipt("q", "quick", "general", ("en",), (), CAPTURED, CAPTURED, (), 0)


def job_for(user, cipher, *, question, area=None, countries=()):
    """A drawn area is only ever a standalone general question, as the request rules insist."""
    job = production_job(user, cipher)
    request = replace(
        job.request,
        question=question,
        research_area=area,
        research_mode=ResearchMode.QUICK if area is not None else None,
        devils_advocacy=False,
    )
    return replace(job, request=request, now=NOW, countries=countries)


def service(interference=None):
    return AreaContextService(PackagedAreaGeography(), None, interference)


@pytest.fixture
def store():
    return Store(
        [
            event("E1", Category.AVIATION, 30.5, 50.4, title="Tracked aircraft"),
            event("E2", Category.MARITIME, 30.6, 50.5, title="Tracked vessel"),
        ]
    )


async def test_an_ordinary_question_over_a_country_reads_no_instrument(user, container, store):
    job = job_for(user, container.cipher, question="Assess the coalition talks.", countries=("UA",))
    context = await service().build(job, None, (), store)
    assert context is not None and context.instruments == ()
    assert "No spatial instrument was read" in context.describe()
    assert store.queries == []


async def test_a_drawn_area_reads_the_instruments_and_says_what_it_found(user, container, store):
    job = job_for(user, container.cipher, question="What is happening here?", area=KYIV_REGION)
    context = await service(Cells()).build(job, None, (), store)
    assert context is not None
    found = {row.instrument: row for row in context.instruments}
    assert set(found) == {"aircraft_activity", "vessel_activity"}
    assert found["aircraft_activity"].inside == 1
    assert "Instrument: Aircraft currently tracked" in context.describe()


async def test_a_named_effect_without_a_drawn_area_still_reads_that_instrument(
    user, container, store
):
    job = job_for(
        user,
        container.cipher,
        question="Assess shadow fleet vessel movements off Odesa.",
        countries=("UA",),
    )
    context = await service().build(job, None, (), store)
    assert context is not None
    assert [row.instrument for row in context.instruments] == ["vessel_activity"]


async def test_attaching_leaves_the_receipt_alone_without_a_service_or_a_receipt(user, container):
    job = job_for(user, container.cipher, question="Anything.", area=KYIV_REGION)
    selection = Selection((), 0, 0)
    assert await attach_area_context(None, job, None, selection, RECEIPT, Store()) is RECEIPT
    assert await attach_area_context(service(), job, None, selection, None, Store()) is None
    same = await attach_area_context(service(), job, None, selection, RECEIPT, Store(), selection)
    assert same is RECEIPT


async def test_an_unresolvable_scope_leaves_the_receipt_without_a_context(user, container):
    job = job_for(user, container.cipher, question="Assess vessel movements.")
    attached = await attach_area_context(
        service(), job, None, Selection((), 0, 0), RECEIPT, Store()
    )
    assert attached is RECEIPT and attached.area_context is None


async def test_a_resolvable_scope_attaches_the_context_to_the_receipt(user, container, store):
    job = job_for(user, container.cipher, question="What is happening here?", area=KYIV_REGION)
    attached = await attach_area_context(service(), job, None, Selection((), 0, 0), RECEIPT, store)
    assert attached is not None and attached.area_context is not None
    assert attached.area_context.scope.basis == "drawn_area"
