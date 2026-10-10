"""Fresh report production rechecks public primary and folded retained source rights."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ase.application.report_jobs.snapshots import freeze_job
from ase.application.reports.request import ReportRequest
from ase.container.report_job_gate import ReportJobSourceDisabled, check_job
from ase.domain.errors import Forbidden
from ase.domain.evidence import CorroborationMember
from ase.domain.research import ResearchBatch, ResearchMode
from ase.domain.research_plan import ResearchPlan
from ase.domain.source_licences import SourceLicence, SourceLicencePolicy
from report_documents_helpers import document_records
from report_input_helpers import CallbackGateway, actor_headers, model_setup, report_payload
from report_job_helpers import job
from report_job_snapshot_helpers import private_store


class EmptyCollection:
    def __init__(self):
        self.collect = AsyncMock(return_value=ResearchBatch())

    def plan(self, query):
        return ResearchPlan(query.question, query.since, query.until, query.languages, (), 1, 1, 1)


def policy(*acknowledged, commercial=True):
    return SourceLicencePolicy(
        [
            SourceLicence("allowed", "allowed", True, "terms"),
            SourceLicence("permission", "licence_required", True, "terms"),
            SourceLicence("prohibited", "forbidden", True, "terms"),
        ],
        commercial_use=commercial,
        acknowledgements=frozenset(acknowledged),
    )


async def public_parent(container, user, source_id, *, member):
    record, version = document_records(user.id)
    record.scope = {"research_focus": "general", "research_mode": "quick"}
    evidence = tuple(
        replace(item, source_id="allowed", corroboration=()) for item in version.evidence
    )
    first = (
        replace(
            evidence[0],
            corroboration=(
                CorroborationMember(
                    "folded-copy", source_id, source_id, source_id, "Public report"
                ),
            ),
        )
        if member
        else replace(evidence[0], source_id=source_id)
    )
    version = replace(version, evidence=(first, *evidence[1:]))
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    return record, version


@pytest.mark.parametrize("source_id", ["permission", "prohibited", "unknown"])
@pytest.mark.parametrize("member", [False, True])
@pytest.mark.parametrize("operation", ["followup", "regenerate"])
async def test_public_retained_source_is_rejected_before_fresh_collection_or_model(
    client, container, admin, user, source_id, member, operation
):
    await model_setup(client, container, admin)
    container.research = EmptyCollection()
    collect = container.research.collect
    record, _ = await public_parent(container, user, source_id, member=member)
    # An acknowledgement must never override an explicit prohibition or unknown metadata.
    container.source_licences = policy("prohibited", "unknown")
    gateway = CallbackGateway()
    container.llm = gateway
    headers = await actor_headers(client, user)
    assert (await client.get(f"/api/reports/{record.id}", headers=headers)).status_code == 200
    if operation == "followup":
        response = await client.post(
            "/api/reports",
            headers=headers,
            json=report_payload(research_focus="general", parent_report_id=str(record.id)),
        )
    else:
        response = await client.post(f"/api/reports/{record.id}/versions", headers=headers)
    assert response.status_code == 403, response.text[:500]
    assert "licence terms" in response.text
    assert gateway.requests == []
    collect.assert_not_awaited()


@pytest.mark.parametrize("member", [False, True])
@pytest.mark.parametrize("baseline", [False, True])
@pytest.mark.parametrize("restored", [False, True])
async def test_prepared_public_reuse_rechecks_changed_policy_before_fresh_work(
    client, container, admin, user, member, baseline, restored
):
    await model_setup(client, container, admin)
    collection = EmptyCollection()
    container.research = collection
    record, _ = await public_parent(container, user, "permission", member=member)
    request = ReportRequest(
        template_id="ask",
        question="What changed?",
        research_mode=ResearchMode.QUICK,
        parent_report_id=None if baseline else record.id,
        automation=baseline,
        subscription_previous_report_id=record.id if baseline else None,
    )
    container.source_licences = policy("permission")
    async with container.session_factory() as session:
        prepared, routing = await container.generate_report(session).prepare_job(user, request)
    if restored:
        stored = job(
            owner_id=user.id,
            payload={
                "schema_version": 1,
                "input": freeze_job(prepared, routing, container.source_profiles, private_store),
            },
        )
    container.source_licences = policy()
    container.source_admission = SimpleNamespace(
        enabled_many=AsyncMock(
            side_effect=lambda ids: {key: container.source_licences.allowed(key) for key in ids}
        )
    )
    gateway = CallbackGateway()
    container.llm = gateway
    async with container.session_factory() as session:
        if restored:
            with pytest.raises(ReportJobSourceDisabled):
                await check_job(container, session, stored)
        else:
            with pytest.raises(Forbidden, match="licence terms"):
                await container.generate_report(session).produce_prepared(prepared, routing)
    assert gateway.requests == []
    collection.collect.assert_not_awaited()


@pytest.mark.parametrize(
    ("source_id", "acknowledged", "commercial"),
    [("allowed", (), True), ("permission", ("permission",), True), ("prohibited", (), False)],
)
async def test_permitted_public_corroboration_can_produce_a_fresh_followup(
    client, container, admin, user, source_id, acknowledged, commercial
):
    await model_setup(client, container, admin)
    container.research = EmptyCollection()
    record, _ = await public_parent(container, user, source_id, member=True)
    container.source_licences = policy(*acknowledged, commercial=commercial)
    response = await client.post(
        "/api/reports",
        headers=await actor_headers(client, user),
        json=report_payload(research_focus="general", parent_report_id=str(record.id)),
    )
    assert response.status_code == 201, response.text[:500]
