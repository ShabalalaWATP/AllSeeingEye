"""Alert templates must be executable from the rule's retained inputs."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest

from ase.application.dto import RequestContext
from ase.application.warning.indicators import IndicatorInput
from ase.container.alert_reports import AlertReportAdmission
from ase.domain.collection import AreaOfInterest, CollectionPlan, Pir
from ase.domain.errors import InvalidRequest
from feeds_helpers import make_event
from helpers import USER_EMAIL, USER_PASSWORD, bearer, login_token
from report_job_api_helpers import job_settings, prepared, stored, work
from test_alert_report_queue import current_alert
from test_research_area import area

__all__ = ["job_settings"]


async def test_create_and_update_reject_missing_template_inputs(client, user):
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    valid = {"name": "Rule", "report_template": "intsum"}
    created = (await client.post("/api/warning/indicators", headers=headers, json=valid)).json()
    for template, countries, reason in (
        ("country_brief", [], "one country"),
        ("country_brief", ["UA", "PL"], "one country"),
        ("ask", [], "collection plan"),
        ("area_brief", [], "collection plan"),
        ("conflict_assessment", [], "conflict"),
        ("disaster_sitrep", [], "hazard"),
    ):
        body = {**valid, "report_template": template, "countries": countries}
        for method, path, values in (
            (client.post, "/api/warning/indicators", body),
            (
                client.put,
                f"/api/warning/indicators/{created['id']}",
                {**body, "expected_updated_at": created["updated_at"]},
            ),
        ):
            response = await method(path, headers=headers, json=values)
            assert response.status_code == 422, (template, response.text)
            assert reason in response.json()["error"]["fields"]["report_template"]


@pytest.mark.parametrize("legacy_template", ["ask", "retired_template"])
async def test_legacy_incompatible_rule_can_pause_and_recover(
    container, client, user, legacy_template
):
    gateway, headers = await prepared(container, client)
    async with container.session_factory() as session:
        rule = await container.create_indicator(session).execute(
            user, IndicatorInput("Legacy", report_template="intsum"), RequestContext()
        )
        await container.repositories(session).indicators.save(
            replace(rule, report_template=legacy_template)
        )
        await session.commit()
    alert = (await container.build_evaluator().run_once())[0]
    await AlertReportAdmission(container).tick()
    failed = await current_alert(container, alert.id)
    assert (failed.report_status, failed.report_error) == ("failed", "admission_failed")
    assert not gateway.calls
    path = f"/api/warning/indicators/{rule.id}"
    paused = await client.put(
        path,
        headers=headers,
        json={
            "name": rule.name,
            "report_template": legacy_template,
            "enabled": False,
            "expected_updated_at": rule.updated_at.isoformat(),
        },
    )
    assert paused.status_code == 200, paused.text
    refused = await client.put(
        path,
        headers=headers,
        json={
            "name": rule.name,
            "report_template": legacy_template,
            "enabled": True,
            "expected_updated_at": paused.json()["updated_at"],
        },
    )
    assert refused.status_code == 422
    repaired = await client.put(
        path,
        headers=headers,
        json={
            "name": rule.name,
            "report_template": "intsum",
            "enabled": True,
            "expected_updated_at": paused.json()["updated_at"],
        },
    )
    assert repaired.status_code == 200, repaired.text


@pytest.mark.parametrize(
    "template",
    [
        "intsum",
        "intrep",
        "aviation_activity",
        "maritime_activity",
        "cyber_summary",
        "country_brief",
        "ask",
        "area_brief",
    ],
)
async def test_each_offered_template_produces_a_frozen_report(container, client, user, template):
    gateway, _ = await prepared(container, client)
    plan_id = None
    async with container.session_factory() as session:
        if template in {"ask", "area_brief"}:
            plan_id = uuid4()
            await container.repositories(session).plans.add(
                CollectionPlan(
                    plan_id,
                    "Plan",
                    "",
                    None,
                    (),
                    (Pir("P1", "What changed?"),),
                    True,
                    user.id,
                    container.clock.now(),
                    container.clock.now(),
                )
            )
            await session.commit()
        countries = ("UA",) if template == "country_brief" else ()
        if countries:
            container.store.upsert(
                [
                    make_event(
                        "ukraine",
                        country_iso="UA",
                        published_at=container.clock.now(),
                        observed_at=container.clock.now(),
                    )
                ]
            )
        await container.create_indicator(session).execute(
            user,
            IndicatorInput(
                "Report", report_template=template, plan_id=plan_id, countries=countries
            ),
            RequestContext(),
        )
    alert = (await container.build_evaluator().run_once())[0]
    await AlertReportAdmission(container).tick()
    queued = await current_alert(container, alert.id)
    assert queued.report_status == "queued", queued.report_error
    if plan_id:
        job = await stored(container, queued.report_job_id)
        assert job.payload["input"]["scope"]["question"] == "What changed?"
    await work(container)
    completed = await current_alert(container, alert.id)
    assert completed.report_id is not None and gateway.calls
    async with container.session_factory() as session:
        report = await container.repositories(session).reports.get(UUID(str(completed.report_id)))
        assert report.template == template


@pytest.mark.parametrize("broken", ["question", "area", "polygon", "wrong_scope"])
async def test_linked_plan_prerequisites_are_checked_before_rule_save(container, user, broken):
    now = container.clock.now()
    plan = CollectionPlan(
        uuid4(),
        "Broken",
        "",
        uuid4() if broken != "question" else None,
        (),
        () if broken == "question" else (Pir("P1", "What changed?"),),
        True,
        user.id,
        now,
        now,
    )
    async with container.session_factory() as session:
        if broken in {"polygon", "wrong_scope"}:
            await container.repositories(session).aois.add(
                AreaOfInterest(
                    plan.aoi_id,
                    "Area",
                    "geometry" if broken == "polygon" else "countries",
                    None,
                    (),
                    user.id if broken == "polygon" else uuid4(),
                    now,
                    research_area=area() if broken == "polygon" else None,
                )
            )
        await container.repositories(session).plans.add(plan)
        await session.commit()
        with pytest.raises(InvalidRequest) as caught:
            await container.create_indicator(session).execute(
                user,
                IndicatorInput("Rule", plan_id=plan.id, report_template="ask"),
                RequestContext(),
            )
        assert "plan_id" in caught.value.fields


async def test_legacy_nine_country_report_can_pause_but_must_be_repaired_to_resume(
    container, client, user
):
    countries = ["UA", "PL", "GB", "US", "FR", "DE", "IT", "ES", "CA"]
    async with container.session_factory() as session:
        rule = await container.create_indicator(session).execute(
            user, IndicatorInput("Legacy countries", countries=countries), RequestContext()
        )
        await container.repositories(session).indicators.save(
            replace(rule, report_template="intsum")
        )
        await session.commit()
    headers = bearer(await login_token(client, USER_EMAIL, USER_PASSWORD))
    path = f"/api/warning/indicators/{rule.id}"
    body = {
        "name": rule.name,
        "countries": countries,
        "report_template": "intsum",
        "enabled": False,
        "expected_updated_at": rule.updated_at.isoformat(),
    }
    paused = await client.put(path, headers=headers, json=body)
    assert paused.status_code == 200, paused.text
    assert paused.json()["countries"] == countries
    body["expected_updated_at"] = paused.json()["updated_at"]
    invalid = await client.put(path, headers=headers, json={**body, "countries": ["ZZ"]})
    assert invalid.status_code == 422
    resumed = await client.put(path, headers=headers, json={**body, "enabled": True})
    assert resumed.status_code == 422
    repaired = await client.put(
        path,
        headers=headers,
        json={
            **body,
            "enabled": True,
            "report_template": None,
        },
    )
    assert repaired.status_code == 200, repaired.text
    assert repaired.json()["countries"] == countries
