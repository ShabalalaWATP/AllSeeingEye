"""Automatic claims travel through real creation, regeneration and schedule persistence."""

import json
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from ase.adapters.persistence.claim_models import ClaimRow
from ase.adapters.persistence.claims import SqlClaimRepository
from ase.adapters.persistence.models import LlmUsageRow, ReportRow, ReportVersionRow
from ase.application.ports.feeds import EventQuery
from ase.application.reports.request import ReportRequest
from ase.domain.claim_generation import ClaimGenerationStatus
from ase.domain.llm import LlmResult
from ase.domain.schedules import Schedule
from production_integration_helpers import StageGateway
from report_helpers import filled_store
from team_helpers import CONTEXT
from test_generate_claims import setup_model


class ClaimGateway(StageGateway):
    async def complete(self, base_url, api_key, model, request):
        if request.schema_name != "claim_proposals":
            return await super().complete(base_url, api_key, model, request)
        self.before_call()
        self.calls.append(request.schema_name)
        evidence = json.loads(request.messages[1].content)["evidence"]
        return LlmResult(
            json.dumps(
                {
                    "claims": [
                        {
                            "statement": f"The source reports: {row['title']}",
                            "kind": "reported_fact",
                            "citations": [
                                {
                                    "label": row["label"],
                                    "relation": "supporting",
                                    "field": "title",
                                    "text": row["title"],
                                }
                            ],
                            "unresolved_conflicts": [],
                        }
                        for row in evidence[:2]
                    ]
                }
            ),
            "claims-returned-model",
            20,
            7,
            4,
        )


async def prepare(container, user):
    await setup_model(container, user)
    container.store.upsert(list(filled_store().query(EventQuery(limit=10))))


async def test_creation_and_regeneration_keep_exact_initial_claims(container, user):
    await prepare(container, user)
    async with container.session_factory() as session:

        def no_transaction():
            assert not session.in_transaction()

        container.llm = ClaimGateway(no_transaction)
        record, first = await container.generate_report(session).execute(
            user, ReportRequest("ask", question="What was reported?"), CONTEXT
        )
        assert first.claim_generation.status is ClaimGenerationStatus.COMPLETED
        assert len(first.claim_generation.revision_ids) == 2
        _, second = await container.generate_report(session).regenerate(user, record.id, CONTEXT)
        assert second.number == 2
        assert set(first.claim_generation.revision_ids).isdisjoint(
            second.claim_generation.revision_ids
        )
        r = container.repositories(session)
        assert (
            await r.reports.get_version(record.id, 1)
        ).claim_generation == first.claim_generation
        assert (
            await r.reports.get_version(record.id, 2)
        ).claim_generation == second.claim_generation
        assert (await r.claims.scope_usage(user.id, None))[0] == 4
        assert [call for call in container.llm.calls if call == "claim_proposals"] == [
            "claim_proposals"
        ] * 2
        usage = await r.llm_usage.list_recent(20)
        assert len([item for item in usage if item.purpose == "claim_proposals"]) == 2


async def test_schedule_uses_same_automatic_pipeline(container, user):
    await prepare(container, user)
    container.llm = ClaimGateway()
    now = container.clock.now()
    schedule = Schedule(
        uuid4(), "Daily research", "intsum", None, None, 6, "daily", 0, 48, True, user.id, now, now
    )
    report_id = await container.schedule_report(schedule)
    async with container.session_factory() as session:
        version = await container.repositories(session).reports.get_version(report_id, 1)
        assert version.claim_generation.status is ClaimGenerationStatus.COMPLETED
        assert len(version.claim_generation.revision_ids) == 2


async def test_claim_failure_rolls_back_report_and_usage_in_real_pipeline(
    container, user, monkeypatch
):
    await prepare(container, user)
    container.llm = ClaimGateway()
    original = SqlClaimRepository.create
    count = 0

    async def fail_second(self, *args):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("Simulated second claim failure")
        return await original(self, *args)

    monkeypatch.setattr(SqlClaimRepository, "create", fail_second)
    async with container.session_factory() as session:
        with pytest.raises(RuntimeError):
            await container.generate_report(session).execute(
                user, ReportRequest("ask", question="What was reported?"), CONTEXT
            )
        assert not session.in_transaction()
    async with container.session_factory() as session:
        for table in (ReportRow, ReportVersionRow, ClaimRow, LlmUsageRow):
            assert await session.scalar(select(func.count()).select_from(table)) == 0
