"""External generation must recheck linked scope and concurrent report edits."""

from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ase.application.access import AccessContext
from ase.application.reports.authorisation import ReportAuthorisation
from ase.application.reports.request import ReportRequest
from ase.domain.collection import AreaOfInterest, CollectionPlan, Pir
from ase.domain.errors import InvalidRequest, NotFound, StaleReportVersion
from ase.domain.report_records import ReportRecord
from ase.domain.reports import ReportStatus
from mfa_boundary_support import NOW, actor


def prepared():
    user = actor()
    plan = CollectionPlan(
        uuid4(), "Plan", "", uuid4(), (), (Pir("P1", "Question"),), True, user.id, NOW, NOW
    )
    aoi = AreaOfInterest(plan.aoi_id, "Area", "countries", None, ("GB",), user.id, NOW)
    access, reports, plans, aois, uow = (AsyncMock() for _ in range(5))
    access.context.return_value = AccessContext(user, {}, {})
    access.background.return_value = access.context.return_value
    plans.get.return_value = plan
    aois.get.return_value = aoi
    auth = ReportAuthorisation(access, reports, plans, aois, uow)
    request = ReportRequest("country-brief", plan_id=plan.id)
    return user, plan, aoi, access, reports, plans, aois, uow, auth, request


@pytest.mark.parametrize("state", ["matching", "missing", "foreign"])
async def test_collection_area_must_exist_in_same_scope(state: str) -> None:
    user, plan, aoi, _access, _reports, _plans, aois, _uow, auth, request = prepared()
    aois.get.return_value = (
        None
        if state == "missing"
        else replace(aoi, created_by=uuid4())
        if state == "foreign"
        else aoi
    )
    if state == "matching":
        assert await auth.prepare(user, request) == plan
    else:
        with pytest.raises(NotFound):
            await auth.prepare(user, request)


async def test_generation_rejects_changed_plan_after_external_work() -> None:
    user, plan, _aoi, access, _reports, plans, _aois, uow, auth, request = prepared()
    plans.get.return_value = replace(plan, updated_at=NOW + timedelta(seconds=1))
    with pytest.raises(InvalidRequest, match="plan changed"):
        await auth.finish(user, request, None, plan)
    uow.rollback.assert_awaited_once()
    access.context.assert_awaited_once_with(user, for_update=True)
    uow.commit.assert_not_awaited()


@pytest.mark.parametrize("state", ["deleted", "new_version", "unchanged"])
async def test_regeneration_cannot_overwrite_concurrent_report_change(state: str) -> None:
    user, plan, _aoi, _access, reports, _plans, _aois, _uow, auth, request = prepared()
    record = ReportRecord(
        uuid4(), "country-brief", "Report", {}, NOW, NOW, NOW, ReportStatus.READY, user.id, NOW, 1
    )
    reports.get.return_value = (
        None
        if state == "deleted"
        else replace(record, latest_version=2)
        if state == "new_version"
        else record
    )
    if state == "unchanged":
        await auth.finish(user, request, record, plan)
    else:
        with pytest.raises(NotFound if state == "deleted" else StaleReportVersion):
            await auth.finish(user, request, record, plan)
