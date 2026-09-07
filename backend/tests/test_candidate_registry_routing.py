"""Real fixture-backed adapters execute explicit candidate subjects under shared budgets."""

from dataclasses import replace
from datetime import timedelta

import pytest

from ase.adapters.research_records.companies_house import CompaniesHouseProvider
from ase.adapters.research_records.companies_house_client import CompaniesHouseClient
from ase.adapters.research_records.companies_house_people import (
    CompaniesHouseOfficersProvider,
    CompaniesHousePscProvider,
)
from ase.adapters.research_records.company import SecSubmissionsProvider
from ase.adapters.research_records.gleif import GleifParentProvider, GleifProfileProvider
from ase.application.research.collection import ResearchCollector
from ase.application.research.pacing import PacedProvider, RequestPacer
from ase.domain.registry_identifiers import RegistryIdentifier
from ase.domain.research import CollectionStatus, ResearchFocus
from ase.domain.research_tasks import PlannedQueryTask, ResearchCandidate
from research_records_helpers import CLOCK, QUERY, RecordService, submissions
from test_companies_house import KEY, profile
from test_organisation_relationships import LEI, gleif_profile, parent_record, people


def candidate_query(source, namespace="sec_cik", value="1234", **changes):
    candidate = ResearchCandidate(
        "candidate",
        "Unverified company",
        registry_identifiers=(RegistryIdentifier("registry", namespace, value),),
    )
    task = PlannedQueryTask(
        "lookup",
        source,
        "disambiguation",
        (),
        candidate.id,
        route="candidate_identifier",
        identifier_id="registry",
    )
    return replace(
        QUERY,
        focus=ResearchFocus.COMPANY,
        subject="Unknown name",
        source_ids=(source,),
        candidate_hypotheses=(candidate,),
        planned_tasks=(task,),
        **changes,
    )


@pytest.mark.parametrize(
    "kind", ["sec", "gleif", "direct", "ultimate", "company", "officers", "psc"]
)
async def test_every_registry_routes_to_exact_constructed_endpoint(monkeypatch, kind):
    data = (
        submissions()
        if kind == "sec"
        else gleif_profile()
        if kind == "gleif"
        else (
            parent_record(kind)
            if kind in {"direct", "ultimate"}
            else profile()
            if kind == "company"
            else people("officers" if kind == "officers" else "persons-with-significant-control")
        )
    )
    service = RecordService(monkeypatch, data)
    client = CompaniesHouseClient(service.http, CLOCK, KEY)
    provider = {
        "sec": lambda: SecSubmissionsProvider(service.http, CLOCK),
        "gleif": lambda: GleifProfileProvider(service.http, CLOCK),
        "direct": lambda: GleifParentProvider(service.http, CLOCK, "direct"),
        "ultimate": lambda: GleifParentProvider(service.http, CLOCK, "ultimate"),
        "company": lambda: CompaniesHouseProvider(service.http, CLOCK, client=client),
        "officers": lambda: CompaniesHouseOfficersProvider(client, CLOCK),
        "psc": lambda: CompaniesHousePscProvider(client, CLOCK),
    }[kind]()
    namespace, original = (
        ("sec_cik", "cik:1234")
        if kind == "sec"
        else (
            ("lei", LEI.lower())
            if kind in {"gleif", "direct", "ultimate"}
            else ("gb_company_number", "companies-house:1234567")
        )
    )
    query = candidate_query(
        provider.id, namespace, original, until=CLOCK.now() + timedelta(seconds=1)
    )
    # UK profile supports a name baseline; skip only that baseline to isolate exact routing.
    result = await ResearchCollector([PacedProvider(provider, RequestPacer())]).collect(
        query, skip_task_ids=frozenset({"source:" + provider.id})
    )
    try:
        assert len(service.requests) == 1
        attempt = result.attempts[0]
        assert attempt.status is CollectionStatus.COMPLETED
        assert result.items
        assert attempt.registry_lookup.original_value == original
        assert attempt.registry_lookup == result.plan.tasks[1].registry_lookup
        assert provider.supports(replace(query, subject=attempt.registry_lookup.subject))
        expected = (
            "CIK0000001234.json" if kind == "sec" else LEI if namespace == "lei" else "01234567"
        )
        assert expected in str(service.requests[0].url)
        assert query.subject not in str(service.requests[0].url)
        assert query.question not in str(service.requests[0].url)
    finally:
        await service.http.aclose()


async def test_unsupported_name_baseline_and_two_candidates_use_distinct_subjects(monkeypatch):
    service = RecordService(monkeypatch, submissions())
    provider = SecSubmissionsProvider(service.http, CLOCK)
    query = candidate_query(provider.id)
    second = replace(
        query.candidate_hypotheses[0],
        id="second",
        registry_identifiers=(RegistryIdentifier("registry", "sec_cik", "9999"),),
    )
    query = replace(
        query,
        candidate_hypotheses=(*query.candidate_hypotheses, second),
        planned_tasks=(
            *query.planned_tasks,
            replace(query.planned_tasks[0], id="second", candidate_id="second"),
        ),
    )
    try:
        result = await ResearchCollector([provider]).collect(query)
        assert len(service.requests) == 2
        assert [row.registry_lookup.subject for row in result.attempts[1:]] == [
            "CIK:0000001234",
            "CIK:0000009999",
        ]
        assert result.attempts[0].status is CollectionStatus.UNSUPPORTED
        assert result.attempts[1].status is CollectionStatus.COMPLETED
        # Fixture echoes 1234, so the second requested identity is rejected, never relabelled.
        assert result.attempts[2].status is CollectionStatus.FAILED
    finally:
        await service.http.aclose()


@pytest.mark.parametrize("number", ["sc123456", "R1234567", "OC12345A", "123"])
async def test_uk_canonical_numbers_are_accepted_by_real_adapter(monkeypatch, number):
    service = RecordService(monkeypatch)
    provider = CompaniesHouseOfficersProvider(CompaniesHouseClient(service.http, CLOCK, KEY), CLOCK)
    query = candidate_query(provider.id, "gb_company_number", number)
    try:
        result = await ResearchCollector([provider]).collect(query)
        assert len(service.requests) == 1
        lookup = result.plan.tasks[1].registry_lookup
        assert provider.supports(replace(query, subject=lookup.subject))
        assert lookup.subject.removeprefix("GB:") in str(service.requests[0].url)
    finally:
        await service.http.aclose()


async def test_country_and_source_capability_do_not_widen(monkeypatch):
    service = RecordService(monkeypatch)
    provider = CompaniesHouseProvider(service.http, CLOCK, KEY)
    try:
        for query in (
            candidate_query(provider.id, "gb_company_number", "1234", country_iso="CN"),
            candidate_query(provider.id, "lei", LEI),
        ):
            result = await ResearchCollector([provider]).collect(
                query, skip_task_ids=frozenset({"source:" + provider.id})
            )
            assert result.attempts[0].status is CollectionStatus.UNSUPPORTED
        assert not service.requests
    finally:
        await service.http.aclose()
