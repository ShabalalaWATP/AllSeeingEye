"""Capacity retries must not monopolise the bounded admission page."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

from ase.adapters.persistence.alert_reports import SqlAlertReportQueue
from ase.adapters.persistence.warning_mapping import _alert_row
from ase.application.report_jobs.service import ReportJobService
from ase.application.warning.report_snapshot import snapshot_to_dict
from ase.container.alert_reports import AlertReportAdmission
from ase.domain.errors import RateLimited
from helpers import USER_PASSWORD, create_user
from report_job_api_helpers import job_settings, prepared
from test_alert_report_queue import current_alert, rule

__all__ = ["job_settings"]


async def test_capacity_backlog_yields_to_a_later_eligible_owner(
    container, client, user, clock, monkeypatch
):
    gateway, _ = await prepared(container, client)
    blocked_rule = await rule(container, user)
    blocked_alert = (await container.build_evaluator().run_once())[0]
    # Forty simultaneous firings are five complete eight-item pages.
    async with container.session_factory() as session:
        original_snapshot = await SqlAlertReportQueue(session).snapshot(blocked_alert.id)
        assert original_snapshot is not None
        for _ in range(39):
            row = _alert_row(replace(blocked_alert, id=uuid4()))
            row.report_rule_revision = blocked_rule.updated_at
            row.report_next_attempt_at = blocked_alert.fired_at
            row.report_snapshot = snapshot_to_dict(
                replace(
                    original_snapshot, origin=replace(original_snapshot.origin, alert_id=row.id)
                )
            )
            session.add(row)
        await session.commit()
    clock.advance(timedelta(seconds=1))
    peer = await create_user(container, email="eligible@example.com", password=USER_PASSWORD)
    await rule(container, peer)
    eligible = (await container.build_evaluator().run_once())[0]
    original = ReportJobService.prepare_candidate

    async def full_for_one_owner(self, actor, *args, **kwargs):
        if actor.id == user.id:
            raise RateLimited(60)
        return await original(self, actor, *args, **kwargs)

    monkeypatch.setattr(ReportJobService, "prepare_candidate", full_for_one_owner)
    admission = AlertReportAdmission(container)
    for _ in range(5):
        assert await admission.tick() == 8
        clock.advance(timedelta(minutes=1))
    # The first blocked batch is now due again. The untouched eligible intent comes first.
    assert await admission.tick() == 8
    queued = await current_alert(container, eligible.id)
    assert queued.report_status == "queued" and queued.report_job_id is not None
    assert (await current_alert(container, blocked_alert.id)).report_status == "pending"
    assert not gateway.calls
