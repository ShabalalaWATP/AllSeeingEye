"""Alert reports must retain the exact rule scope and triggering evidence."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from ase.adapters.persistence.alert_reports import SqlAlertReportQueue
from ase.application.warning.report_admission import alert_report_request
from ase.application.warning.report_snapshot import (
    capture_report,
    snapshot_from_dict,
    snapshot_to_dict,
)
from ase.container.alert_reports import AlertReportAdmission
from ase.domain.events import Category, Point
from ase.domain.warning import alert_from, evaluate
from feeds_helpers import make_event
from report_job_api_helpers import job_settings, prepared, stored, work
from test_alert_report_queue import current_alert, rule
from test_warning import NOW, indicator

__all__ = ["job_settings"]


def test_two_country_five_minute_rule_never_becomes_global_or_hour_long():
    rule = replace(
        indicator(),
        countries=("UA", "PL"),
        window_minutes=5,
        report_template="intsum",
        categories=(Category.CONFLICT,),
        keywords=("rail",),
    )
    event = make_event(
        "trigger",
        title="Rail disruption",
        country_iso="UA",
        category=Category.CONFLICT,
        published_at=NOW - timedelta(minutes=2),
        observed_at=NOW,
    )
    firing = evaluate(rule, [event], NOW, None)
    assert firing is not None
    alert = alert_from(rule, firing, uuid4(), NOW)
    request = alert_report_request(rule, alert)
    assert request.country_isos == ("UA", "PL")
    assert request.research_since == NOW - timedelta(minutes=5)
    assert request.research_until == NOW + timedelta(microseconds=1)
    assert request.categories == (Category.CONFLICT,)


@pytest.mark.parametrize("corruption", ["version", "extra", "evidence_identity"])
def test_snapshot_codec_rejects_unrecognised_or_mismatched_records(corruption):
    current = indicator(report_template="intsum")
    event = make_event(
        "trigger",
        title="Kharkiv",
        country_iso="UA",
        category=Category.CONFLICT,
        published_at=NOW,
        observed_at=NOW,
    )
    firing = evaluate(current, [event], NOW, None)
    alert = alert_from(current, firing, uuid4(), NOW)
    data = snapshot_to_dict(capture_report(current, alert, firing, {}))
    if corruption == "version":
        data["version"] = 2
    elif corruption == "extra":
        data["origin"]["unrecognised_filter"] = "unsafe"
    else:
        data["origin"]["event_ids"] = ["different-event"]
    with pytest.raises(ValueError):
        snapshot_from_dict(data)


async def test_report_keeps_original_scope_and_evidence_after_live_eviction(
    container, client, user, clock
):
    gateway, _ = await prepared(container, client)
    await rule(
        container,
        user,
        countries=("UA", "PL"),
        categories=(Category.CONFLICT,),
        keywords=("rail",),
        severity_floor=0.7,
        window_minutes=5,
    )
    now = clock.now()
    trigger = make_event(
        "original-trigger",
        source_id="usgs_earthquakes",
        title="Rail disruption",
        country_iso="UA",
        category=Category.CONFLICT,
        published_at=now,
        observed_at=now,
        severity=0.8,
    )
    polish = replace(trigger, id="polish-trigger", country_iso="PL")
    excluded = [
        replace(trigger, id="outside-country", country_iso="GB"),
        replace(trigger, id="outside-time", published_at=now - timedelta(minutes=6)),
        replace(trigger, id="outside-category", category=Category.NEWS),
        replace(trigger, id="outside-keywords", title="Road disruption"),
        replace(trigger, id="outside-severity", severity=0.6),
        replace(trigger, id="future", published_at=now + timedelta(seconds=1)),
    ]
    container.store.upsert([trigger, polish, *excluded])
    alert = (await container.build_evaluator().run_once())[0]
    assert alert.count == 2 and set(alert.event_ids) == {trigger.id, polish.id}
    container.store.put([replace(trigger, title="Changed after the firing")])
    container.store.prune(now + timedelta(days=800))
    assert container.store.get(trigger.id) is None
    clock.advance(timedelta(hours=2))
    await AlertReportAdmission(container).tick()
    queued = await current_alert(container, alert.id)
    assert queued.report_status == "queued", queued.report_error
    job = await stored(container, queued.report_job_id)
    origin = job.payload["input"]["scope"]["alert_origin"]
    assert origin["countries"] == ["UA", "PL"] and origin["keywords"] == ["rail"]
    assert origin["categories"] == ["conflict"] and origin["severity_floor"] == 0.7
    assert origin["matched_count"] == 2 and origin["rule_id"] == str(alert.indicator_id)
    assert job.payload["input"]["period_from"] == (now - timedelta(minutes=5)).isoformat()
    assert {row["title"] for row in job.payload["input"]["evidence"]} == {"Rail disruption"}
    await work(container)
    completed = await current_alert(container, alert.id)
    assert completed.report_id is not None and gateway.calls
    async with container.session_factory() as session:
        report = await container.repositories(session).reports.get(completed.report_id)
        version = await container.repositories(session).reports.get_version(completed.report_id, 1)
    assert report.scope["alert_origin"] == origin
    assert {row.event_id for row in version.evidence} == {trigger.id, polish.id}


async def test_box_snapshot_preserves_rule_geography_and_bounded_sample(container, client, user):
    await prepared(container, client)
    await rule(
        container,
        user,
        bbox=(170, -10, -170, 10),
        categories=(Category.CONFLICT,),
        keywords=("rail",),
        severity_floor=0.7,
        window_minutes=5,
    )
    trigger = make_event(
        "base",
        source_id="usgs_earthquakes",
        title="Rail disruption",
        severity=0.8,
        category=Category.CONFLICT,
        published_at=container.clock.now(),
        observed_at=container.clock.now(),
        point=Point(175, 0),
    )
    container.store.upsert(
        [
            *(replace(trigger, id=f"inside-{index}") for index in range(25)),
            replace(trigger, id="outside", point=Point(0, 0)),
            replace(trigger, id="no-location", point=None),
        ]
    )
    alert = (await container.build_evaluator().run_once())[0]
    async with container.session_factory() as session:
        snapshot = await SqlAlertReportQueue(session).snapshot(alert.id)
    assert snapshot.origin.matched_count == 25 and len(snapshot.evidence) == 20
    assert snapshot.origin.bbox.west == 170 and snapshot.origin.bbox.east == -170
    assert all(row.event_id.startswith("inside-") for row in snapshot.evidence)
    assert "not the complete matched population" in snapshot.origin.describe()
    await AlertReportAdmission(container).tick()
    await work(container)
    current = await current_alert(container, alert.id)
    async with container.session_factory() as session:
        version = await container.repositories(session).reports.get_version(current.report_id, 1)
    assert any(
        row.rule == "alert_evidence_sample" and "25 alert matches" in row.message
        for row in version.findings
    )
