"""Licence vetoes cover polling, private providers and administrator bypass paths."""

from unittest.mock import AsyncMock, Mock

import pytest

import ase.container as composition
from ase.adapters.feeds.firms_runtime import FirmsConnectionProbe
from ase.adapters.persistence.source_controls import SqlSourceAdmission
from ase.application.research.source_admission import ControlledResearchProvider
from ase.container import Container, feed_services
from ase.container.research_allocation import load_research_allocation
from ase.domain.errors import Forbidden
from ase.domain.research import CollectionStatus, ResearchBatch
from ase.domain.source_licences import SourceLicence, SourceLicencePolicy
from event_app_fixtures import email_sender, feed_connectors  # noqa: F401
from feeds_helpers import FakeConnector, make_spec
from helpers import ADMIN_EMAIL, ADMIN_PASSWORD, bearer, login_token
from test_firms_credentials import BASE as FIRMS_BASE
from test_firms_credentials import KEY as FIRMS_KEY
from test_research_collection import QUERY, Provider
from test_source_controls import disable


def policy(*, acknowledged=(), commercial=True):
    return SourceLicencePolicy(
        [
            SourceLicence("fake_feed", "forbidden", True, "terms"),
            SourceLicence("allowed", "allowed", False, "terms"),
            SourceLicence("unknown", "licence_required", True, "terms"),
            SourceLicence("research_google_news_en", "licence_required", True, "terms"),
        ],
        commercial_use=commercial,
        acknowledgements=frozenset(acknowledged),
    )


async def test_licence_veto_is_independent_of_admin_and_exact_acknowledgement(container, admin):
    gate = SqlSourceAdmission(
        container.session_factory,
        licences=policy(acknowledged=("fake_feed", "unknown", "google_news")),
    )
    assert await gate.enabled_many(
        ("fake_feed", "allowed", "unknown", "research_google_news_en", "unregistered")
    ) == {
        "fake_feed": False,
        "allowed": True,
        "unknown": True,
        "research_google_news_en": False,
        "unregistered": False,
    }
    await disable(container, admin, "allowed")
    assert not await gate.enabled("allowed")
    parent_gate = SqlSourceAdmission(
        container.session_factory,
        ("google_news",),
        licences=policy(acknowledged=("research_google_news_en",)),
    )
    assert not await parent_gate.enabled("research_google_news_en")


async def test_private_provider_reports_licence_refusal_before_fetch(container):
    gate = SqlSourceAdmission(container.session_factory, licences=policy())
    provider = Provider("fake_feed", ResearchBatch())
    result = await ControlledResearchProvider(provider, gate).collect(QUERY)
    assert provider.called == 0
    assert result.attempts[0].status is CollectionStatus.UNAVAILABLE
    assert "licence terms" in result.attempts[0].explanation
    assert "administrator" not in result.attempts[0].explanation


@pytest.mark.parametrize("action", ["activation", "test", "reset"])
async def test_admin_cannot_override_licence_or_fetch_a_denied_source(
    client, container, admin, monkeypatch, action
):
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    monkeypatch.setattr(container, "source_licences", policy(acknowledged=("fake_feed",)))
    fetch = AsyncMock(return_value=[])
    monkeypatch.setattr(container.connectors[0], "fetch", fetch)
    if action == "activation":
        response = await client.patch(
            "/api/admin/sources/fake_feed/activation",
            headers=bearer(token),
            json={"enabled": True},
        )
    else:
        response = await client.post(
            f"/api/admin/sources/fake_feed/{action}", headers=bearer(token)
        )
    assert response.status_code == 403
    assert "licence terms" in response.text
    fetch.assert_not_called()


async def test_denied_source_can_still_be_disabled(client, container, admin, monkeypatch):
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    monkeypatch.setattr(container, "source_licences", policy())
    response = await client.patch(
        "/api/admin/sources/fake_feed/activation",
        headers=bearer(token),
        json={"enabled": False},
    )
    assert response.status_code == 204


async def test_exact_research_acknowledgement_needs_no_logical_parent_ack(container, admin):
    source_id = "research_google_news_en"
    licences = policy(acknowledged=(source_id,))
    gate = SqlSourceAdmission(container.session_factory, licences=licences)
    context = await load_research_allocation((source_id,), admission=gate)
    assert context.authorised_ids == {source_id}
    assert not await gate.enabled("google_news")  # Unknown fetched products still fail closed.
    environmental = SqlSourceAdmission(
        container.session_factory, ("google_news",), licences=licences
    )
    blocked = await load_research_allocation((source_id,), admission=environmental)
    assert not blocked.authorised_ids
    await disable(container, admin, "google_news_watchlists")
    assert not (await load_research_allocation((source_id,), admission=gate)).authorised_ids


async def test_scheduler_does_not_start_or_resume_licence_denied_tasks(container):
    scheduler = container.scheduler
    scheduler._licences = policy()
    gate = SqlSourceAdmission(container.session_factory, licences=policy())
    scheduler.poller._admission = gate
    connector = container.connectors[0]
    await scheduler.start()
    try:
        assert scheduler.running and "fake_feed" not in scheduler._tasks
        with pytest.raises(Forbidden, match="licence terms"):
            scheduler.resume("fake_feed")
        outcome = await scheduler.poll_once(connector)
        assert not outcome.ok and "licence terms" in outcome.error
        assert connector.calls == 0 and container.store.stats().total == 0
        health = container.health.get("fake_feed")
        assert health.status_reason == "licence_unavailable"
        assert "licence terms" in health.blocked_reason and health.polls == 0
    finally:
        await scheduler.stop()


def test_policy_validation_precedes_service_construction(settings, monkeypatch):
    rejected = Mock(side_effect=ValueError("Invalid source licence metadata"))
    email = Mock()
    monkeypatch.setattr(composition, "load_source_licences", rejected)
    monkeypatch.setattr(composition, "build_email_sender", email)
    with pytest.raises(ValueError, match="Invalid source licence metadata"):
        Container(settings)
    email.assert_not_called()


async def test_default_catalogue_ids_are_validated_at_startup(settings, clock):
    container = Container(settings, clock=clock)
    try:
        assert container.connectors
        assert container.source_licences.commercial_use is False
    finally:
        await container.dispose()


def test_new_runtime_catalogue_source_requires_reviewed_metadata(container, monkeypatch):
    monkeypatch.setattr(
        feed_services,
        "build_connectors",
        lambda *args, **kwargs: [FakeConnector(make_spec("new-unreviewed-feed"))],
    )
    with pytest.raises(ValueError, match="Missing source licence metadata: new-unreviewed-feed"):
        feed_services.build_feed_connectors(container, None)


async def test_container_wires_immutable_commercial_policy_before_polling(settings, clock):
    settings = settings.model_copy(update={"commercial_use": True})
    container = Container(settings, clock=clock, connectors=())
    try:
        assert container.source_licences.commercial_use
        # No schema is needed to reject an unknown commercial product.
        assert not await container.source_admission.enabled("unregistered-source")
        assert not container.scheduler._licences.allowed("unregistered-source")
    finally:
        await container.dispose()


@pytest.mark.parametrize("action", ["test", "confirm"])
async def test_firms_probe_and_activation_cannot_bypass_licence_policy(
    client, container, admin, monkeypatch, action
):
    token = await login_token(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    headers = bearer(token)
    probe = AsyncMock(return_value=0)
    monkeypatch.setattr(FirmsConnectionProbe, "test", probe)
    draft = await client.put(
        FIRMS_BASE + "/draft",
        headers=headers,
        json={
            "api_key": FIRMS_KEY,
            "expected_revision": 0,
        },
    )
    assert draft.status_code == 200
    monkeypatch.setattr(container, "source_licences", policy())
    body = {"expected_revision": 1}
    if action == "confirm":
        body["test_generation"] = 1
    response = await client.post(FIRMS_BASE + "/" + action, headers=headers, json=body)
    assert response.status_code == 403 and "licence terms" in response.text
    probe.assert_not_called()


def test_firms_resume_never_starts_an_unacknowledged_sensor(container, monkeypatch):
    licences = SourceLicencePolicy(
        [SourceLicence("firms_viirs_noaa20", "licence_required", True, "terms")],
        commercial_use=True,
        acknowledgements=frozenset({"firms_viirs_noaa20"}),
    )
    monkeypatch.setattr(container, "source_licences", licences)
    resume = Mock()
    monkeypatch.setattr(container.scheduler, "resume", resume)
    container._resume_firms()
    resume.assert_called_once_with("firms_viirs_noaa20")
