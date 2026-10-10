"""Fresh reports recheck private source permission, including frozen jobs after restart."""

from dataclasses import replace

import pytest

from ase.application.report_jobs.snapshots import freeze_job, restore_job
from ase.application.reports.request import ReportRequest
from ase.domain.errors import Forbidden
from ase.domain.evidence import CorroborationMember
from ase.domain.research import ResearchFocus, ResearchMode
from photo_helpers import upload
from report_documents_helpers import document_records
from report_input_helpers import (
    CallbackGateway,
    actor_headers,
    model_setup,
    report_payload,
    saved_parent,
    stored_input,
)
from report_job_snapshot_helpers import private_store
from test_commercial_private_inputs import private_policy


@pytest.mark.parametrize("media", [False, True])
async def test_fresh_report_cannot_use_saved_input_without_exact_permission(
    client, container, admin, user, media
):
    collection = await model_setup(client, container, admin)
    input_id = upload(container, user) if media else stored_input(container, user).receipt.id
    # A document task cannot disguise a media input using the other acknowledgement.
    container.source_licences = private_policy("research_import") if media else private_policy()
    gateway = CallbackGateway()
    container.llm = gateway
    response = await client.post(
        "/api/reports",
        headers=await actor_headers(client, user),
        json=report_payload(research_input_id=str(input_id)),
    )
    assert response.status_code == 403, response.text[:500]
    assert gateway.requests == [] and collection.calls == 0


async def test_acknowledged_document_input_can_be_used(client, container, admin, user):
    collection = await model_setup(client, container, admin)
    stored = stored_input(container, user)
    container.source_licences = private_policy("research_import")
    response = await client.post(
        "/api/reports",
        headers=await actor_headers(client, user),
        json=report_payload(research_input_id=str(stored.receipt.id)),
    )
    assert response.status_code == 201, response.text
    assert collection.calls == 0


@pytest.mark.parametrize("operation", ["followup", "regenerate"])
async def test_saved_report_stays_readable_but_fresh_reuse_requires_permission(
    client, container, admin, user, operation
):
    await model_setup(client, container, admin)
    record, _ = await saved_parent(container, user)
    container.source_licences = private_policy()
    gateway = CallbackGateway()
    container.llm = gateway
    headers = await actor_headers(client, user)
    assert (await client.get(f"/api/reports/{record.id}", headers=headers)).status_code == 200
    if operation == "followup":
        response = await client.post(
            "/api/reports", headers=headers, json=report_payload(parent_report_id=str(record.id))
        )
    else:
        response = await client.post(f"/api/reports/{record.id}/versions", headers=headers)
    assert response.status_code == 403, response.text[:500]
    assert gateway.requests == []


@pytest.mark.parametrize("media", [False, True])
@pytest.mark.parametrize("restored", [False, True])
async def test_prepared_private_job_rechecks_new_process_policy_before_model(
    client, container, admin, user, media, restored
):
    collection = await model_setup(client, container, admin)
    input_id = upload(container, user) if media else stored_input(container, user).receipt.id
    request = ReportRequest(
        template_id="ask",
        question="What does the private input establish?",
        research_mode=ResearchMode.QUICK,
        research_focus=ResearchFocus.DOCUMENT,
        research_input_id=input_id,
    )
    async with container.session_factory() as session:
        job, routing = await container.generate_report(session).prepare_job(user, request)
    if restored:
        job = restore_job(
            freeze_job(job, routing, container.source_profiles, private_store), user, job.profile
        )
        assert job.reused_evidence and not job.seed_events
    container.source_licences = private_policy("research_import") if media else private_policy()
    gateway = CallbackGateway()
    container.llm = gateway
    async with container.session_factory() as session:
        with pytest.raises(Forbidden, match="licence terms"):
            await container.generate_report(session).produce_prepared(job, routing)
    assert gateway.requests == [] and collection.calls == 0


@pytest.mark.parametrize("member", [False, True])
@pytest.mark.parametrize("operation", ["followup", "regenerate_general"])
async def test_inherited_media_evidence_needs_its_own_permission(
    client, container, admin, user, member, operation
):
    await model_setup(client, container, admin)
    record, version = document_records(user.id)
    record.scope = {
        "research_focus": "document" if operation == "followup" else "general",
        "research_mode": "quick",
    }
    # The acknowledged document source must not mask a refusal of the media source.
    evidence = tuple(replace(item, source_id="research_import") for item in version.evidence)
    first = evidence[0]
    first = (
        replace(
            first,
            corroboration=(
                CorroborationMember("private-copy", "research_media", "Media", "private", "Photo"),
            ),
        )
        if member
        else replace(first, source_id="research_media")
    )
    version = replace(version, evidence=(first, *evidence[1:]))
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    container.source_licences = private_policy("research_import")
    gateway = CallbackGateway()
    container.llm = gateway
    headers = await actor_headers(client, user)
    if operation == "followup":
        response = await client.post(
            "/api/reports", headers=headers, json=report_payload(parent_report_id=str(record.id))
        )
    else:
        response = await client.post(f"/api/reports/{record.id}/versions", headers=headers)
    assert response.status_code == 403, response.text[:500]
    assert gateway.requests == []
