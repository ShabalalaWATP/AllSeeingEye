"""Prepared jobs freeze linked scope and release reads before durable execution."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from ase.application.reports.production_result import ProductionResult
from ase.application.reports.request import ReportRequest
from ase.domain.collection import CollectionPlan, Pir
from ase.domain.errors import InvalidRequest
from ase.domain.research import ResearchMode
from llm_fixture_helpers import seed_legacy_profile
from production_integration_helpers import StageGateway
from report_documents_helpers import document_records
from report_helpers import PROFILE


async def test_prepare_pins_parent_version_and_makes_no_model_call(container, user):
    gateway = StageGateway()
    container.llm = gateway
    await seed_legacy_profile(container, PROFILE)
    record, version = document_records(user.id)
    async with container.session_factory() as session:
        await container.repositories(session).reports.add(record, version)
        await session.commit()
    async with container.session_factory() as session:
        service = container.generate_report(session)
        job, routing = await service.prepare_job(
            user,
            ReportRequest(
                "ask",
                question="What changed?",
                research_mode=ResearchMode.QUICK,
                parent_report_id=record.id,
            ),
        )
        assert job.request.parent_version == 1
        assert job.scope["parent_version"] == 1
        assert job.reused_evidence == version.evidence
        assert routing.required(job.template.role).id == job.profile.id
        assert not session.in_transaction()
    assert gateway.calls == []


async def test_prepared_job_rejects_changed_plan_and_does_not_save(container, user):
    await seed_legacy_profile(container, PROFILE)
    now = container.clock.now()
    plan = CollectionPlan(
        uuid4(),
        "Plan",
        "Frozen description",
        None,
        ("UA",),
        (Pir("PIR-1", "What changed?"),),
        True,
        user.id,
        now,
        now,
    )
    async with container.session_factory() as session:
        await container.repositories(session).plans.add(plan)
        await session.commit()
        service = container.generate_report(session)
        job, routing = await service.prepare_job(user, ReportRequest("ask", plan_id=plan.id))
        assert job.request.question == "What changed?"
        assert job.scope["collection_plan_revision"]["updated_at"] == now.isoformat()
        assert job.background == "Frozen description"
        await container.repositories(session).plans.save(
            replace(plan, updated_at=now + timedelta(seconds=1))
        )
        await session.commit()
        _, version = document_records(user.id)

        async def produce(_job, _routing, before_persist, **_kwargs):
            await before_persist()
            return ProductionResult(version)

        with (
            patch.object(service._producer, "produce_with_claims", side_effect=produce),
            pytest.raises(InvalidRequest, match="plan changed"),
        ):
            await service.produce_prepared(job, routing)
        assert await container.repositories(session).reports.get(version.report_id) is None


async def test_produce_prepared_forwards_checkpoint_and_final_hook_without_saving(container, user):
    await seed_legacy_profile(container, PROFILE)
    async with container.session_factory() as session:
        service = container.generate_report(session)
        job, routing = await service.prepare_job(user, ReportRequest("intsum"))
        _, version = document_records(user.id)
        checkpoint, progress = object(), AsyncMock()

        async def released_fence():
            assert not session.in_transaction()

        fence = AsyncMock(side_effect=released_fence)

        async def produce(_job, _routing, before_persist, **kwargs):
            assert kwargs == {"checkpoints": checkpoint, "progress": progress}
            await before_persist()
            return ProductionResult(version)

        with patch.object(service._producer, "produce_with_claims", side_effect=produce):
            result = await service.produce_prepared(
                job, routing, checkpoints=checkpoint, progress=progress, before_persist=fence
            )
        fence.assert_awaited_once()
        assert result.version.model_routing == routing.provenance
        assert await container.repositories(session).reports.get(version.report_id) is None
