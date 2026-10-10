"""Commercial permission changes fence frozen alert evidence before paid work."""

import pytest
from sqlalchemy import func, select

from ase.adapters.persistence.report_job_models import ReportJobRow
from ase.adapters.persistence.source_controls import SqlSourceAdmission
from ase.container.alert_reports import AlertReportAdmission
from ase.domain.source_licences import SourceLicence, SourceLicencePolicy
from report_job_api_helpers import job_settings, prepared, work
from test_alert_report_queue import current_alert, rule

__all__ = ["job_settings"]


@pytest.mark.parametrize("acknowledged", [False, True], ids=["denied", "permitted"])
@pytest.mark.parametrize("queued", [False, True], ids=["before-admission", "before-execution"])
async def test_frozen_alert_uses_current_commercial_permission(
    container, client, user, queued, acknowledged
):
    gateway, _ = await prepared(container, client)
    await rule(container, user)
    alert = (await container.build_evaluator().run_once())[0]
    if queued:
        await AlertReportAdmission(container).tick()
        assert (await current_alert(container, alert.id)).report_status == "queued"

    # A restart may enable commercial mode after the alert's evidence was saved.
    # Install the same policy in both real composition boundaries, without mocking
    # the retained-evidence gate or the durable worker.
    policy = SourceLicencePolicy(
        [
            SourceLicence(
                "usgs_earthquakes",
                "licence_required",
                True,
                "docs/SOURCE_LICENCES.md#source-usgs_earthquakes",
            ),
        ],
        commercial_use=True,
        acknowledgements=frozenset({"usgs_earthquakes"}) if acknowledged else frozenset(),
    )
    container.source_licences = policy
    container.source_admission = SqlSourceAdmission(container.session_factory, licences=policy)
    if queued:
        await work(container)
    else:
        await AlertReportAdmission(container).tick()

    if acknowledged:
        if not queued:
            await work(container)
        current = await current_alert(container, alert.id)
        assert current.report_status == "needs_review"
        assert current.report_id is not None and gateway.calls
        assert await AlertReportAdmission(container).tick() == 0
        return

    current = await current_alert(container, alert.id)
    assert current.report_id is None
    assert gateway.calls == []
    assert current.report_status == ("paused" if queued else "failed")
    assert current.report_error == ("source_disabled" if queued else "admission_failed")
    async with container.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ReportJobRow)) == int(queued)
    assert await AlertReportAdmission(container).tick() == 0
