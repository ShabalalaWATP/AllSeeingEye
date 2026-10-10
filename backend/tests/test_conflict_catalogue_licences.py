"""Raw conflict metadata is descriptive inventory, not operational permission."""

from uuid import uuid4

import pytest

from ase.application.dto import RequestContext
from ase.application.reports.request import ReportRequest
from ase.application.schedules.definition import ScheduleInput
from ase.container.report_job_gate import release_job
from ase.domain.errors import Forbidden
from ase.domain.source_licences import SourceLicence, SourceLicencePolicy
from llm_fixture_helpers import seed_legacy_profile
from report_helpers import PROFILE


def policy(*, commercial=True, acknowledged=False):
    return SourceLicencePolicy(
        (
            SourceLicence("reference:conflicts", "licence_required", True, "terms"),
            *(
                SourceLicence(f"ukraine:{name}", "allowed", True, "terms")
                for name in ("viina_control", "oryx_losses", "hrmmu_casualties")
            ),
        ),
        commercial_use=commercial,
        acknowledgements=frozenset({"reference:conflicts"}) if acknowledged else frozenset(),
    )


@pytest.mark.parametrize("template", ["conflict_assessment", "intsum"])
async def test_new_conflict_context_requires_permission_before_model_work(
    container, user, template
):
    await seed_legacy_profile(container, PROFILE)
    container.source_licences = policy()
    async with container.session_factory() as session:
        service = container.generate_report(session)
        with pytest.raises(Forbidden, match="licence terms"):
            await service.prepare_job(user, ReportRequest(template, conflict_id="ukraine"))


@pytest.mark.parametrize("commercial,acknowledged", [(False, False), (True, True)])
async def test_permitted_conflict_context_remains_available(
    container, user, commercial, acknowledged
):
    await seed_legacy_profile(container, PROFILE)
    container.source_licences = policy(commercial=commercial, acknowledged=acknowledged)
    async with container.session_factory() as session:
        job, _ = await container.generate_report(session).prepare_job(
            user, ReportRequest("conflict_assessment", conflict_id="ukraine")
        )
    assert "Belligerents: Russia, Ukraine" in job.background


async def test_ordinary_report_and_disaster_tracker_do_not_need_conflict_permission(
    container, user
):
    await seed_legacy_profile(container, PROFILE)
    container.source_licences = policy()
    async with container.session_factory() as session:
        job, _ = await container.generate_report(session).prepare_job(user, ReportRequest("intsum"))
    assert job.background is None
    assert all(card.activity.last_7d == 0 for card in container.trackers().disaster_board())
    assert container.conflicts.get("ukraine") is not None  # Descriptive inventory remains intact.


@pytest.mark.parametrize("operation", ["board", "detail"])
def test_direct_tracker_conflict_consumption_is_guarded(container, operation):
    container.source_licences = policy()
    service = container.trackers()
    with pytest.raises(Forbidden, match="licence terms"):
        if operation == "board":
            service.conflict_board()
        else:
            service.conflict_detail("ukraine")


def test_ukraine_requires_conflict_permission_even_when_its_other_datasets_are_allowed(container):
    container.source_licences = policy()
    with pytest.raises(Forbidden, match="licence terms"):
        container.ukraine()


async def test_conflict_subscription_create_and_update_are_guarded(container, user):
    data = ScheduleInput("Conflict updates", "conflict_assessment", conflict_id="ukraine")
    async with container.session_factory() as session:
        existing = await container.create_schedule(session).execute(user, data, RequestContext())
    container.source_licences = policy()
    async with container.session_factory() as session:
        with pytest.raises(Forbidden, match="licence terms"):
            await container.create_schedule(session).execute(user, data, RequestContext())
        await session.rollback()
        with pytest.raises(Forbidden, match="licence terms"):
            await container.update_schedule(session).execute(
                user, existing.id, data, RequestContext()
            )


async def test_frozen_conflict_job_cannot_resume_under_a_new_licence_veto(container, user):
    await seed_legacy_profile(container, PROFILE)
    async with container.session_factory() as session:
        stored = await container.report_jobs(session).prepare_candidate(
            user, uuid4(), ReportRequest("conflict_assessment", conflict_id="ukraine")
        )
        assert "Belligerents" in stored.payload["input"]["background"]
    container.source_licences = policy()
    async with container.session_factory() as session:
        with pytest.raises(Forbidden, match="licence terms"):
            await container.report_job_gate(session, stored)
        await session.rollback()
        # Reading retained progress does not admit the frozen background into new work.
        await release_job(container, session, stored)
