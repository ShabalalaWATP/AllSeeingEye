"""Immutable preview/export replay, same-scope authority and render-time release checks."""

import asyncio
import json
from dataclasses import replace
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import update

from annotation_comparison_helpers import prepared
from ase.adapters.persistence.claims import SqlClaimRepository
from ase.adapters.persistence.models import ReportRow, UserRow
from ase.application.reports import annotation_comparisons, comparison_manifest
from ase.application.reports.comparison_inputs import ComparisonInput, ComparisonSelection
from ase.application.reports.comparison_manifest import comparison_json
from ase.application.reports.evidence_package import _PACKAGE_SLOTS
from ase.domain.errors import Conflict, InvalidRequest, NotFound, RateLimited, Unauthenticated
from test_claim_repository import seed
from test_saved_map_views import claims_for


async def test_exact_historical_replay_survives_new_revision_(client, container, user):
    actor, report, _, revision, request = await prepared(client, container, user)
    async with container.session_factory() as session:
        service = container.annotation_comparisons(session)
        preview = await service.execute(actor, request)
        assert not session.in_transaction()
        next_revision = replace(
            revision, id=uuid4(), number=2, previous_id=revision.id, reason="Later correction"
        )
        assert await SqlClaimRepository(session).append(next_revision, revision.id)
        await session.commit()
        exported = await service.execute(actor, request, preview.comparison_sha256)
        manifest = json.loads(exported.content)
        assert manifest["comparison_sha256"] == preview.comparison_sha256
        assert manifest["before"]["revisions"][0]["id"] == str(revision.id)
        assert manifest["after"]["revisions"][0]["id"] == str(revision.id)
        assert manifest["method_version"] == "ase-annotation-comparison-v1"
        assert manifest["before"]["report_id"] == str(report.id)


@pytest.mark.parametrize("change", ["method", "output"])
async def test_changed_comparison_policy_or_results_require_new_preview(
    client, container, user, monkeypatch, change
):
    actor, _, _, _, request = await prepared(client, container, user)
    async with container.session_factory() as session:
        service = container.annotation_comparisons(session)
        preview = await service.execute(actor, request)
        if change == "method":
            monkeypatch.setattr(annotation_comparisons, "COMPARISON_METHOD", "future-comparison")
        else:
            monkeypatch.setattr(annotation_comparisons, "annotation_deltas", lambda *args: ())
        with pytest.raises(Conflict, match="Preview again"):
            await service.execute(actor, request, preview.comparison_sha256)


async def test_admin_cannot_combine_different_personal_owners(client, container, admin, user):
    actor = await claims_for(client, container, admin)
    mine, _, _ = await seed(container, admin)
    other, _, _ = await seed(container, user)
    async with container.session_factory() as session:
        with pytest.raises(InvalidRequest, match="same personal owner or team"):
            await container.annotation_comparisons(session).execute(
                actor,
                ComparisonInput(ComparisonSelection(mine.id, 1), ComparisonSelection(other.id, 1)),
            )


@pytest.mark.parametrize(
    "mutation,error", [("account", Unauthenticated), ("report", NotFound), ("content", Conflict)]
)
async def test_both_sides_are_rechecked_after_rendering(client, container, user, mutation, error):
    actor, report, _, _, request = await prepared(client, container, user)
    entered, finish = Event(), Event()

    def render(value):
        entered.set()
        assert finish.wait(10)
        return comparison_json(value)

    async with container.session_factory() as session:
        service = container.annotation_comparisons(session)
        preview = await service.execute(actor, request)
        service.renderer = render
        task = asyncio.create_task(service.execute(actor, request, preview.comparison_sha256))
        try:
            assert await asyncio.to_thread(entered.wait, 10)
            async with container.session_factory() as other:
                if mutation == "account":
                    await other.execute(
                        update(UserRow).where(UserRow.id == user.id).values(is_active=False)
                    )
                elif mutation == "report":
                    await container.repositories(other).reports.delete(report.id)
                else:
                    await other.execute(
                        update(ReportRow)
                        .where(ReportRow.id == report.id)
                        .values(title="Changed while rendering")
                    )
                await other.commit()
        finally:
            finish.set()
        with pytest.raises(error):
            await task


async def test_preview_and_export_share_bounded_workers_and_manifest_bytes(
    client, container, user, monkeypatch
):
    actor, _, _, _, request = await prepared(client, container, user)
    async with container.session_factory() as session:
        service = container.annotation_comparisons(session)
        assert _PACKAGE_SLOTS.acquire(blocking=False) and _PACKAGE_SLOTS.acquire(blocking=False)
        try:
            with pytest.raises(RateLimited):
                await service.execute(actor, request)
        finally:
            _PACKAGE_SLOTS.release()
            _PACKAGE_SLOTS.release()
        monkeypatch.setattr(comparison_manifest, "MAX_COMPARISON_BYTES", 100)
        with pytest.raises(InvalidRequest, match="manifest limit"):
            await service.execute(actor, request)


async def test_cancelled_render_keeps_admission_until_worker_finishes(client, container, user):
    actor, _, _, _, request = await prepared(client, container, user)
    entered, finish, exited = Event(), Event(), Event()

    def render(value):
        entered.set()
        try:
            assert finish.wait(10)
            return comparison_json(value)
        finally:
            exited.set()

    async with container.session_factory() as session:
        service = container.annotation_comparisons(session)
        service.renderer = render
        task = asyncio.create_task(service.execute(actor, request))
        try:
            assert await asyncio.to_thread(entered.wait, 10)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert _PACKAGE_SLOTS.acquire(blocking=False)
            try:
                assert not _PACKAGE_SLOTS.acquire(blocking=False)
            finally:
                _PACKAGE_SLOTS.release()
        finally:
            finish.set()
            assert await asyncio.to_thread(exited.wait, 10)
            # Await the worker callback before another test uses shared admission.
            for _ in range(100):
                await asyncio.sleep(0.001)
                if _PACKAGE_SLOTS.acquire(blocking=False):
                    second = _PACKAGE_SLOTS.acquire(blocking=False)
                    _PACKAGE_SLOTS.release()
                    if second:
                        _PACKAGE_SLOTS.release()
                        break
            else:
                pytest.fail("Cancelled render did not release admission after worker completion")
