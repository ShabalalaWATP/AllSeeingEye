"""Async HTTP session checks happen before the final guarded private-object release."""

import json
from dataclasses import asdict
from datetime import timedelta

import pytest

from annotation_comparison_helpers import prepared
from annotation_monitor_helpers import correct, seeded
from ase.api.routers import annotation_monitors
from ase.api.session_fence import SessionFence
from ase.application.reports.annotation_comparisons import AnnotationComparisons
from helpers import USER_PASSWORD, bearer, login_token
from team_helpers import CONTEXT
from test_annotation_monitoring import tick


@pytest.mark.parametrize("export", [False, True])
async def test_comparison_parent_deleted_during_async_http_check_never_releases_snapshot(
    client, container, user, monkeypatch, export
):
    actor, report, _, _, request = await prepared(client, container, user)
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    payload = json.loads(json.dumps(asdict(request), default=str))
    path = "/api/annotation-comparisons"
    if export:
        async with container.session_factory() as session:
            preview = await container.annotation_comparisons(session).execute(actor, request)
        payload["expected_comparison_sha256"] = preview.comparison_sha256
        path += "/export"
    original = SessionFence.confirm

    async def guarded_check(fence, **options):
        await original(fence, **options)
        async with container.session_factory() as session:
            await container.delete_report(session).execute(user, report.id, CONTEXT)

    monkeypatch.setattr(SessionFence, "confirm", guarded_check)
    response = await client.post(path, headers=headers, json=payload)
    assert response.status_code == 404, response.text
    assert "source_content_hash" not in response.text


@pytest.mark.parametrize("export", [False, True])
async def test_monitor_parent_deleted_during_async_http_check_never_releases_retained_transition(
    client, container, user, monkeypatch, export
):
    actor, report, _, claim, monitor = await seeded(client, container, user)
    await correct(container, actor, claim)
    assert await tick(container, monitor.id)
    async with container.session_factory() as session:
        transitions, _ = await container.annotation_monitors(session).repository.history(
            monitor.id, 20, 0
        )
    headers = bearer(await login_token(client, user.email, USER_PASSWORD))
    path = f"/api/annotation-monitors/{monitor.id}/transitions/{transitions[0].id}"
    original = SessionFence.confirm

    async def guarded_check(fence, **options):
        await original(fence, **options)
        async with container.session_factory() as session:
            await container.delete_report(session).execute(user, report.id, CONTEXT)

    monkeypatch.setattr(SessionFence, "confirm", guarded_check)
    if export:
        response = await client.post(
            path + "/export",
            headers=headers,
            json={"expected_comparison_sha256": transitions[0].comparison_sha256},
        )
    else:
        response = await client.get(path, headers=headers)
    assert response.status_code == 404, response.text
    assert "source_content_hash" not in response.text


@pytest.mark.parametrize("kind", ["comparison", "monitor"])
async def test_token_expiring_after_final_guarded_service_denies_release_without_an_await(
    client, container, user, clock, monkeypatch, kind
):
    if kind == "comparison":
        actor, _, _, _, request = await prepared(client, container, user)
        headers = bearer(await login_token(client, user.email, USER_PASSWORD))
        original = AnnotationComparisons.execute

        async def expires_after_commit(self, *args, **kwargs):
            result = await original(self, *args, **kwargs)
            clock.advance(timedelta(days=1))
            return result

        monkeypatch.setattr(AnnotationComparisons, "execute", expires_after_commit)
        response = await client.post(
            "/api/annotation-comparisons",
            headers=headers,
            json=json.loads(json.dumps(asdict(request), default=str)),
        )
    else:
        actor, _, _, claim, monitor = await seeded(client, container, user)
        await correct(container, actor, claim)
        assert await tick(container, monitor.id)
        async with container.session_factory() as session:
            rows, _ = await container.annotation_monitors(session).repository.history(
                monitor.id, 20, 0
            )
        headers = bearer(await login_token(client, user.email, USER_PASSWORD))
        original_transition = annotation_monitors.retained_transition

        async def expires_after_transition(*args, **kwargs):
            result = await original_transition(*args, **kwargs)
            clock.advance(timedelta(days=1))
            return result

        monkeypatch.setattr(annotation_monitors, "retained_transition", expires_after_transition)
        response = await client.get(
            f"/api/annotation-monitors/{monitor.id}/transitions/{rows[0].id}", headers=headers
        )
    assert response.status_code == 401, response.text
    assert "source_content_hash" not in response.text
