"""An exact retained passage is readable only through its authorised report version."""

from dataclasses import replace
from datetime import timedelta

from ase.adapters.persistence.original_passages import SqlOriginalPassageRepository
from ase.adapters.persistence.report_jobs import SqlReportJobRepository
from ase.adapters.persistence.source_controls import SqlSourceControlRepository
from ase.application.research.original_acquisition import (
    OriginalAcquisition,
    OriginalAcquisitionBudget,
)
from ase.domain.evidence import EvidenceItem, quality_of_information
from ase.domain.original_followup import OriginalFollowupReceipt
from ase.domain.research import CollectionAttempt, CollectionStatus, ResearchMode, ResearchQuery
from ase.domain.research_records import ResearchReceipt
from helpers import USER_EMAIL, USER_PASSWORD, bearer, create_user, login_token
from original_acquisition_support import (
    NOW,
    SOURCE,
    Admission,
    Clock,
    Parser,
    access,
    catalogue,
    event,
    policy,
    response,
)
from report_documents_helpers import document_records
from report_job_helpers import job


async def test_original_passage_read_rechecks_report_source_and_expiry(
    client, container, clock, user, admin
):
    clock.advance(timedelta(days=13))
    await create_user(container, email="other-original@example.com", password=USER_PASSWORD)
    container.original_source_policies = {SOURCE: policy()}
    candidate_catalogue = catalogue(owner_id=user.id)
    candidate_id = next(iter(candidate_catalogue.candidates))

    async def current_access():
        return access(user.id)

    async def fetch(request):
        return response()

    acquired = await OriginalAcquisition(
        candidate_catalogue, Admission(), current_access, Parser(), Clock(), fetch
    ).acquire(
        candidate_id,
        policy(),
        OriginalAcquisitionBudget(
            ResearchMode.QUICK,
            remaining_source_operations=1,
            remaining_transport_requests=3,
            remaining_seconds=45,
        ),
    )
    document = acquired.document
    assert document is not None
    record, version = document_records(user.id)
    evidence = EvidenceItem.from_event(
        "E1",
        event(),
        NOW,
        source_name=SOURCE,
        independence_key="",
    )
    version = replace(
        version,
        evidence=(evidence, *version.evidence[1:]),
        quality=quality_of_information((evidence, *version.evidence[1:])),
    )
    stored_job = job(owner_id=user.id, report_id=record.id, version_id=version.id)
    async with container.session_factory() as session:
        await SqlReportJobRepository(session).add(stored_job)
        staged = await SqlOriginalPassageRepository(session).stage(
            job_id=stored_job.id,
            event_id=evidence.event_id,
            evidence_label="E1",
            document=document,
        )
        original = OriginalFollowupReceipt(
            "E1",
            evidence.event_id,
            SOURCE,
            "acquired",
            "original_passage_staged",
            candidate_id,
            staged.id,
            staged.document.passages[0].id,
            staged.document.id,
            1,
            3,
        )
        query = ResearchQuery(
            "What does the issuer state?",
            NOW - timedelta(days=1),
            NOW,
            mode=ResearchMode.QUICK,
        )
        receipt = ResearchReceipt.build(
            query, (CollectionAttempt(SOURCE, SOURCE, CollectionStatus.COMPLETED, 1),), 1
        )
        version = replace(version, research=replace(receipt, original_followup=(original,)))
        await container.repositories(session).reports.add(record, version)
        await session.flush()
        assert await SqlOriginalPassageRepository(session).link(
            job_id=stored_job.id,
            ref=staged.id,
            version_id=version.id,
            owner_id=user.id,
            team_id=None,
            event_id=evidence.event_id,
            evidence_label="E1",
            now=clock.now(),
        )
        await session.commit()

    owner_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    other_token = await login_token(client, "other-original@example.com", USER_PASSWORD)
    route = f"/api/reports/{record.id}/original-passages/{staged.id}?version_number=1"
    allowed = await client.get(route, headers=bearer(owner_token))
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["text"] == "Exact original passage."
    assert allowed.headers["cache-control"] == "no-store"
    foreign = await client.get(route, headers=bearer(other_token))
    assert foreign.status_code == 404
    async with container.session_factory() as session:
        await SqlSourceControlRepository(session).set(SOURCE, False, clock.now(), admin.id)
        await session.commit()
    disabled = await client.get(route, headers=bearer(owner_token))
    assert disabled.status_code == 404
    async with container.session_factory() as session:
        await SqlSourceControlRepository(session).set(SOURCE, True, clock.now(), admin.id)
        await session.commit()
    clock.advance(timedelta(days=2))
    refreshed_token = await login_token(client, USER_EMAIL, USER_PASSWORD)
    expired = await client.get(route, headers=bearer(refreshed_token))
    assert expired.status_code == 404
